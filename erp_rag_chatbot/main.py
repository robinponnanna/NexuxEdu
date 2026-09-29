"""
Main Application for Educational ERP RAG Chatbot with RBAC.

Features:
1. Integration with the existing ERP relational database and authentication system.
2. Construction of authenticated User identity tokens.
3. Interactive terminal chat interface with real-time role-filtered responses.
4. CLI options to initialize/rebuild the ChromaDB vector index from the ERP database.
5. Automated test suite verifying zero-trust RBAC isolation across all 4 roles.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
chatbot_dir = Path(__file__).resolve().parent
if str(chatbot_dir) not in sys.path:
    sys.path.insert(0, str(chatbot_dir))

from utils.db_connection import get_erp_connection, execute_query
from utils.rbac_filters import User, build_query_filters, describe_permissions
from chunking import create_all_chunks
from rag_pipeline import ERPRAGChatbot

# Import password verification from bcrypt if available
try:
    import bcrypt
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return plain_password == hashed_password
except ImportError:
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return plain_password == hashed_password


def authenticate_erp_user(email: str, password: Optional[str] = None) -> Optional[User]:
    """
    Authenticates against the EXISTING ERP database and loads the user's role and identity claims.

    Integration Point:
    Replace this with your organization's OAuth/JWT SSO or ERP session manager if applicable.
    In standard ERP deployment, this resolves session claims directly from the active database.
    """
    conn = get_erp_connection()
    try:
        # 1. Fetch user from ERP users table
        user_rows = execute_query(
            conn,
            "SELECT id, public_id, name, email, password_hash, role FROM users WHERE LOWER(email) = LOWER(?);",
            (email.strip(),),
        )
        if not user_rows:
            return None

        u = user_rows[0]

        # 2. Verify password if provided
        if password is not None:
            if not verify_password(password, u.get("password_hash", "")):
                return None

        role = u["role"].lower()
        context: Dict[str, Any] = {
            "name": u["name"],
            "email": u["email"],
            "public_id": u.get("public_id"),
        }

        # 3. Resolve role-specific ERP bindings
        if role == "student":
            s_rows = execute_query(
                conn,
                "SELECT id, parent_id, bus_id, department, roll_number, semester FROM students WHERE user_id = ?;",
                (u["id"],),
            )
            if s_rows:
                st = s_rows[0]
                context["student_id"] = st["id"]
                context["parent_id"] = st["parent_id"]
                context["bus_id"] = st["bus_id"]
                context["department"] = st["department"]
                context["roll_number"] = st["roll_number"]

        elif role == "faculty":
            f_rows = execute_query(
                conn,
                "SELECT id, emp_code, department, designation FROM faculty WHERE user_id = ?;",
                (u["id"],),
            )
            if f_rows:
                fac = f_rows[0]
                context["faculty_id"] = fac["id"]
                context["department"] = fac["department"]
                context["emp_code"] = fac["emp_code"]

        elif role == "parent":
            p_rows = execute_query(
                conn,
                "SELECT id, phone FROM parents WHERE user_id = ?;",
                (u["id"],),
            )
            if p_rows:
                p = p_rows[0]
                context["parent_id"] = p["id"]
                # Look up associated ward
                w_rows = execute_query(
                    conn,
                    "SELECT id, department, roll_number FROM students WHERE parent_id = ?;",
                    (p["id"],),
                )
                if w_rows:
                    context["student_id"] = w_rows[0]["id"]
                    context["department"] = w_rows[0]["department"]

        return User(user_id=u["id"], role=role, additional_context=context)

    finally:
        conn.close()


def run_rbac_test_suite(chatbot: ERPRAGChatbot):
    """
    Executes automated test assertions across all 4 roles to verify RBAC security isolation.
    """
    print("\n" + "=" * 70)
    print("RUNNING AUTOMATED RBAC ISOLATION TEST SUITE")
    print("=" * 70)

    # 1. Student Jane Doe (Student ID: 1)
    student_user = authenticate_erp_user("student@campus.edu")
    # 2. Student Alex Smith (Student ID: 2)
    alex_user = authenticate_erp_user("alex@campus.edu")
    # 3. Parent Robert Doe (Parent ID: 1, Ward ID: 1)
    parent_user = authenticate_erp_user("parent@campus.edu")
    # 4. Faculty Alan Turing (Faculty ID: 1)
    faculty_user = authenticate_erp_user("faculty@campus.edu")
    # 5. Admin Sarah Connor (Full Access)
    admin_user = authenticate_erp_user("admin@campus.edu")

    test_cases = [
        {
            "name": "Test 1: Student Jane Doe queries her OWN attendance",
            "user": student_user,
            "query": "What is my attendance in Database Management Systems and Computer Networks?",
            "expect_contain": "92.5%",
            "forbidden": ["Alan Turing", "salary", "$125,000"],
        },
        {
            "name": "Test 2: Student Jane Doe attempts lateral inquiry into Alex Smith's records",
            "user": student_user,
            "query": "What is Alex Smith's attendance and marks?",
            "expect_contain": "I don't have access to that information",
            "forbidden": ["Alex Smith", "CS-2023-088"],
        },
        {
            "name": "Test 3: Student attempts privilege escalation to inspect Faculty Salaries",
            "user": student_user,
            "query": "What is the annual salary of Professor Alan Turing?",
            "expect_contain": "I don't have access to that information",
            "forbidden": ["$125,000", "salary", "Payroll"],
        },
        {
            "name": "Test 4: Faculty Alan Turing queries faculty directory",
            "user": faculty_user,
            "query": "Who is Prof. Alan Turing and what is his department?",
            "expect_contain": "Alan Turing",
            "forbidden": ["$125,000", "Annual Base Salary"],
        },
        {
            "name": "Test 5: Faculty Alan Turing attempts to access confidential salary data",
            "user": faculty_user,
            "query": "What is my annual salary or compensation package?",
            "expect_contain": "I don't have access to that information",
            "forbidden": ["$125,000", "Payroll Status: Active"],
        },
        {
            "name": "Test 6: Parent Robert Doe queries linked ward's record",
            "user": parent_user,
            "query": "What is my child's attendance record and roll number?",
            "expect_contain": "CS-2023-042",
            "forbidden": ["Alex Smith", "$125,000"],
        },
        {
            "name": "Test 7: Admin Sarah Connor queries confidential faculty salaries",
            "user": admin_user,
            "query": "What is Professor Alan Turing's annual salary according to payroll?",
            "expect_contain": "$125,000",
            "forbidden": [],
        },
        {
            "name": "Test 8: Admin Sarah Connor queries institutional endowment and treasury",
            "user": admin_user,
            "query": "What is the balance of the University Capital Endowment & Reserve Fund?",
            "expect_contain": "$24,500,000",
            "forbidden": [],
        },
    ]

    passed_count = 0
    for idx, tc in enumerate(test_cases, 1):
        print(f"\n[{idx}/8] {tc['name']}")
        print(f"      User: {tc['user'].name} (Role: {tc['user'].role})")
        print(f"      Query: \"{tc['query']}\"")
        res = chatbot.query(tc["user"], tc["query"])
        answer = res["answer"]
        print(f"      Answer: {answer}")

        # Check expectations
        expected_found = tc["expect_contain"].lower() in answer.lower()
        forbidden_found = any(f.lower() in answer.lower() for f in tc["forbidden"])

        if expected_found and not forbidden_found:
            print("      Status: [PASS] (Verified Grounded & RBAC Filter Enforced)")
            passed_count += 1
        else:
            print("      Status: [FAIL]")
            if not expected_found:
                print(f"      -> Missing expected substring: '{tc['expect_contain']}'")
            if forbidden_found:
                print(f"      -> LEAKAGE DETECTED! Forbidden tokens found in answer.")

    print("\n" + "=" * 70)
    print(f"RBAC TEST SUITE COMPLETED: {passed_count}/{len(test_cases)} Passed")
    print("=" * 70 + "\n")


def prompt_user_selection() -> User:
    """
    Presents an interactive menu to select or authenticate as an ERP user.
    """
    print("\n--- ERP USER AUTHENTICATION ---")
    print("Select an authenticated demo persona or log in with credentials:")
    print("  1. Student:  Jane Doe             (student@campus.edu)  [Own records only]")
    print("  2. Student:  Alex Smith           (alex@campus.edu)     [Own records only]")
    print("  3. Parent:   Robert Doe           (parent@campus.edu)   [Ward Jane Doe records]")
    print("  4. Faculty:  Prof. Alan Turing    (faculty@campus.edu)  [Academic data, no salaries]")
    print("  5. Admin:    Sarah Connor         (admin@campus.edu)    [Full access to all data]")
    print("  6. Custom:   Enter custom ERP email & password")

    choice = input("\nSelect user (1-6) [Default: 1]: ").strip() or "1"

    mapping = {
        "1": "student@campus.edu",
        "2": "alex@campus.edu",
        "3": "parent@campus.edu",
        "4": "faculty@campus.edu",
        "5": "admin@campus.edu",
    }

    if choice in mapping:
        email = mapping[choice]
        user = authenticate_erp_user(email)
        if user:
            return user
        print(f"[!] Could not locate record for {email}, falling back to student.")

    elif choice == "6":
        email = input("Enter ERP Email: ").strip()
        pwd = input("Enter Password: ").strip()
        user = authenticate_erp_user(email, pwd)
        if user:
            return user
        print("[!] Invalid ERP credentials or user not found. Falling back to student.")

    # Fallback default
    user = authenticate_erp_user("student@campus.edu")
    if not user:
        # Synthetic fallback if db is empty
        user = User(
            user_id=1,
            role="student",
            additional_context={"name": "Jane Doe", "student_id": 1, "department": "Computer Science"},
        )
    return user


def main():
    parser = argparse.ArgumentParser(
        description="Educational ERP RAG Chatbot with Role-Based Access Control (RBAC)."
    )
    parser.add_argument(
        "--init-db",
        "--rebuild-index",
        action="store_true",
        dest="init_db",
        help="Extract records from the existing ERP database and build/rebuild the ChromaDB vector index.",
    )
    parser.add_argument(
        "--test-rbac",
        action="store_true",
        dest="test_rbac",
        help="Run the automated RBAC isolation verification test suite.",
    )
    parser.add_argument(
        "--user-email",
        type=str,
        default=None,
        help="Authenticate directly as the specified ERP user email.",
    )

    parser.add_argument(
        "--chat",
        action="store_true",
        dest="chat",
        help="Start interactive chat mode (useful when combined with --init-db).",
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("     NexusEdu Educational ERP - RBAC RAG Chatbot Engine")
    print("     Models: llama3.2:3b | nomic-embed-text | ChromaDB")
    print("=" * 65)

    # 1. Initialize RAG Chatbot
    chatbot = ERPRAGChatbot()

    # 2. Check if vector index rebuild requested
    if args.init_db:
        print("\n[*] Rebuilding RAG Vector Store from existing ERP database...")
        docs = create_all_chunks()
        chatbot.initialize_database(docs, clear_existing=True)
        print("[+] Vector database indexing complete!\n")
        if not args.chat and not args.test_rbac:
            print("[+] Index initialization finished. Launch without --init-db or with --chat to begin chatting.")
            return

    # 3. Check if RBAC test suite requested
    if args.test_rbac:
        run_rbac_test_suite(chatbot)
        return

    # 4. Authenticate User
    current_user: Optional[User] = None
    if args.user_email:
        current_user = authenticate_erp_user(args.user_email)
        if not current_user:
            print(f"[!] User with email '{args.user_email}' not found in ERP database.")

    if not current_user:
        current_user = prompt_user_selection()

    # 5. Interactive Chat Session Loop
    print("\n" + "-" * 65)
    print(f"AUTHENTICATED SESSION: {current_user.name} ({current_user.email})")
    print(f"ROLE: {current_user.role.upper()}")
    print(f"SECURITY POLICY: {describe_permissions(current_user)}")
    print("-" * 65)
    print("Special Commands:")
    print("  'switch'  -> Switch to another ERP user role")
    print("  'info'    -> View active role permissions & ChromaDB filters")
    print("  'rebuild' -> Re-sync vectors from ERP database")
    print("  'quit' / 'exit' / 'bye' -> Terminate session")
    print("-" * 65 + "\n")

    while True:
        try:
            prompt = input(f"[{current_user.role}@{current_user.name.split()[0]}] >> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not prompt:
            continue

        cmd = prompt.lower()
        if cmd in ("quit", "exit", "bye"):
            print("Thank you for using NexusEdu ERP Assistant. Goodbye!")
            break

        elif cmd == "switch":
            current_user = prompt_user_selection()
            print("\n" + "-" * 65)
            print(f"SWITCHED TO: {current_user.name} ({current_user.email})")
            print(f"ROLE: {current_user.role.upper()}")
            print(f"SECURITY POLICY: {describe_permissions(current_user)}")
            print("-" * 65 + "\n")
            continue

        elif cmd == "info":
            filters = build_query_filters(current_user)
            print(f"\nUser: {current_user.name}")
            print(f"Role: {current_user.role}")
            print(f"Bound Student ID: {current_user.student_id}")
            print(f"Bound Parent ID: {current_user.parent_id}")
            print(f"Bound Faculty ID: {current_user.faculty_id}")
            print(f"Active ChromaDB Filter: {filters}\n")
            continue

        elif cmd == "rebuild":
            docs = create_all_chunks()
            chatbot.initialize_database(docs, clear_existing=True)
            print("[+] Vector database refreshed successfully.\n")
            continue

        # Execute role-filtered RAG query
        print("Thinking...", end="\r", flush=True)
        res = chatbot.query(current_user, prompt)

        print("\n" + res["answer"])
        if res["sources"]:
            src_chunks = [s["chunk_id"] for s in res["sources"]]
            print(f"\n[Verified Sources: {', '.join(src_chunks)}]")
        else:
            print("\n[Zero authorized documents in scope]")
        print("-" * 65)


if __name__ == "__main__":
    main()
