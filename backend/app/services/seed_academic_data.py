import os
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import json
import uuid
import numpy as np
from sqlalchemy import select, delete
from app.core.database import (
    AsyncSessionLocal, User, Student, Subject, SubjectModule,
    Assessment, AssessmentQuestion, StudentQuestionMark,
    StudentEnrollment, LearningMaterial, MaterialPage,
    MaterialChunk, MicroLesson
)
from app.core.security import hash_password
from app.services.seed_data import generate_pseudo_embedding

async def seed_academic_support_data(force_reseed: bool = False):
    async with AsyncSessionLocal() as session:
        # Check if academic data already seeded
        result = await session.execute(select(Subject).limit(1))
        existing_subject = result.scalar_one_or_none()
        
        if existing_subject is not None and not force_reseed:
            print("Academic Support data already seeded.")
            return

        if force_reseed and existing_subject is not None:
            print("Clearing previous academic support tables for fresh enriched seeding...")
            await session.execute(delete(MicroLesson))
            await session.execute(delete(MaterialChunk))
            await session.execute(delete(MaterialPage))
            await session.execute(delete(LearningMaterial))
            await session.execute(delete(StudentQuestionMark))
            await session.execute(delete(StudentEnrollment))
            await session.execute(delete(AssessmentQuestion))
            await session.execute(delete(Assessment))
            await session.execute(delete(SubjectModule))
            await session.execute(delete(Subject))
            await session.flush()

        print("Seeding Enriched Academic Support database (Subjects, Modules, Assessments, Marks, Materials, Micro-Lessons)...")

        # -------------------------------------------------------------
        # 1. Ensure 10 Students Exist (Hero Jane Doe + Alex + 8 others)
        # -------------------------------------------------------------
        password_hash = hash_password("password123")

        students_metadata = [
            {"name": "Jane Doe", "email": "student@campus.edu", "roll": "CS-2023-042", "section": "Section A"},
            {"name": "Alex Smith", "email": "alex@campus.edu", "roll": "CS-2023-088", "section": "Section A"},
            {"name": "Maya Lin", "email": "maya.lin@campus.edu", "roll": "CS-2023-015", "section": "Section A"},
            {"name": "Liam Chen", "email": "liam.chen@campus.edu", "roll": "CS-2023-029", "section": "Section A"},
            {"name": "Priya Sharma", "email": "priya.sharma@campus.edu", "roll": "CS-2023-054", "section": "Section A"},
            {"name": "Carlos Rodriguez", "email": "carlos.r@campus.edu", "roll": "CS-2023-061", "section": "Section B"},
            {"name": "Aisha Patel", "email": "aisha.p@campus.edu", "roll": "CS-2023-072", "section": "Section B"},
            {"name": "David Kim", "email": "david.kim@campus.edu", "roll": "CS-2023-083", "section": "Section B"},
            {"name": "Elena Rossi", "email": "elena.rossi@campus.edu", "roll": "CS-2023-094", "section": "Section B"},
            {"name": "Marcus Vance", "email": "marcus.vance@campus.edu", "roll": "CS-2023-105", "section": "Section B"}
        ]

        student_objs = []
        for meta in students_metadata:
            u_res = await session.execute(select(User).where(User.email == meta["email"]))
            user = u_res.scalar_one_or_none()
            if not user:
                user = User(
                    public_id=str(uuid.uuid4()),
                    name=meta["name"],
                    email=meta["email"],
                    password_hash=password_hash,
                    role="student"
                )
                session.add(user)
                await session.flush()

            s_res = await session.execute(select(Student).where(Student.user_id == user.id))
            student = s_res.scalar_one_or_none()
            if not student:
                student = Student(
                    user_id=user.id,
                    roll_number=meta["roll"],
                    department="Computer Science",
                    semester=6,
                    section=meta["section"]
                )
                session.add(student)
                await session.flush()
            student_objs.append((meta["email"], student))

        # -------------------------------------------------------------
        # 2. Seed 6 Semester 6 Computer Science Subjects
        # -------------------------------------------------------------
        subjects_data = [
            {
                "code": "CS301",
                "name": "Operating Systems",
                "department": "Computer Science",
                "semester": 6,
                "credits": 4,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Process Management & Concurrency", "desc": "Process life cycle, PCB, context switching, inter-process communication (IPC), POSIX threads."},
                    {"num": 2, "co": "CO2", "title": "CPU Scheduling & Synchronization", "desc": "Scheduling algorithms (FCFS, SJF, Round Robin, Multilevel Queue), race conditions, semaphores, mutexes, Banker's deadlock algorithm."},
                    {"num": 3, "co": "CO3", "title": "Memory Management & Virtual Memory", "desc": "Contiguous allocation, paging, segmentation, TLB address translation, page faults, FIFO/LRU/Optimal page replacement algorithms."},
                    {"num": 4, "co": "CO4", "title": "Storage Management & File Systems", "desc": "Disk scheduling (SSTF, SCAN, LOOK), inode structures, directory layouts, allocation methods (contiguous, linked, indexed)."},
                    {"num": 5, "co": "CO5", "title": "I/O Systems & OS Security", "desc": "I/O hardware, DMA, interrupt handling, access matrix, capability lists, protection domains and sandboxing."}
                ]
            },
            {
                "code": "CS302",
                "name": "Database Management Systems",
                "department": "Computer Science",
                "semester": 6,
                "credits": 4,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Relational Data Models & Constraints", "desc": "Relational algebra, tuple relational calculus, integrity constraints, primary/foreign keys and ER diagrams."},
                    {"num": 2, "co": "CO2", "title": "Structured Query Language (SQL)", "desc": "Complex subqueries, window functions, views, triggers, assertions and recursive queries."},
                    {"num": 3, "co": "CO3", "title": "Schema Refinement & Normalization", "desc": "Functional dependencies, 1NF, 2NF, 3NF, Boyce-Codd Normal Form (BCNF), lossless join decomposition, dependency preservation."},
                    {"num": 4, "co": "CO4", "title": "Transaction Processing & Concurrency", "desc": "ACID properties, serializability, conflict serializability, Two-Phase Locking (2PL), deadlock prevention and timestamp ordering."},
                    {"num": 5, "co": "CO5", "title": "Indexing, Storage & Crash Recovery", "desc": "B+ tree indexing, hash indexing, write-ahead logging (WAL), ARIES recovery algorithm and query execution plans."}
                ]
            },
            {
                "code": "CS303",
                "name": "Computer Networks",
                "department": "Computer Science",
                "semester": 6,
                "credits": 4,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Physical & Data Link Layer Protocols", "desc": "OSI & TCP/IP models, framing, bit/byte stuffing, CRC error detection, Sliding Window protocols (Go-Back-N, Selective Repeat)."},
                    {"num": 2, "co": "CO2", "title": "Medium Access Control & Ethernet", "desc": "CSMA/CD, CSMA/CA, pure/slotted ALOHA, collision domains, VLANs, and Spanning Tree Protocol (STP)."},
                    {"num": 3, "co": "CO3", "title": "Network Layer & Routing Protocols", "desc": "IPv4/IPv6 addressing, CIDR subnetting, NAT, Distance Vector (RIP), Link State (OSPF with Dijkstra's algorithm), BGP inter-domain routing."},
                    {"num": 4, "co": "CO4", "title": "Transport Layer Mechanisms", "desc": "TCP 3-way handshake, connection teardown, TCP sliding window, flow control, Reno/Cubic congestion control, UDP sockets."},
                    {"num": 5, "co": "CO5", "title": "Application Layer & Network Security", "desc": "DNS resolution hierarchy, HTTP/1.1 vs HTTP/2 vs HTTP/3, TLS/SSL cryptographic handshake, firewalls and IPSec."}
                ]
            },
            {
                "code": "CS304",
                "name": "Design and Analysis of Algorithms",
                "department": "Computer Science",
                "semester": 6,
                "credits": 4,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Asymptotic Analysis & Divide-and-Conquer", "desc": "Big-O/Omega/Theta notations, Master Theorem, recursion trees, MergeSort, QuickSort, Closest Pair of Points."},
                    {"num": 2, "co": "CO2", "title": "Dynamic Programming Paradigms", "desc": "Optimal substructure, memoization vs tabulation, Longest Common Subsequence (LCS), 0/1 Knapsack, Matrix Chain Multiplication."},
                    {"num": 3, "co": "CO3", "title": "Greedy Strategies & Balanced Trees", "desc": "Huffman coding, Fractional Knapsack, Activity Selection, AVL Tree rotations (LL, RR, LR, RL) and Red-Black properties."},
                    {"num": 4, "co": "CO4", "title": "Graph Algorithms & Network Flow", "desc": "Breadth-First/Depth-First search, Dijkstra, Bellman-Ford, Prim/Kruskal MST, Ford-Fulkerson max-flow theorem."},
                    {"num": 5, "co": "CO5", "title": "NP-Completeness & Approximation", "desc": "P vs NP, polynomial-time reductions, Circuit-SAT, 3-SAT, Vertex Cover, Traveling Salesperson approximation."}
                ]
            },
            {
                "code": "CS305",
                "name": "Software Engineering & Architecture",
                "department": "Computer Science",
                "semester": 6,
                "credits": 3,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Software Lifecycles & Agile Methodologies", "desc": "Waterfall, Spiral, Scrum sprints, user stories, velocity metrics, Kanban and acceptance criteria."},
                    {"num": 2, "co": "CO2", "title": "Requirements Engineering & Modeling", "desc": "Functional vs non-functional requirements, UML diagrams, sequence diagrams, statecharts and use case specifications."},
                    {"num": 3, "co": "CO3", "title": "Software Architecture & Design Patterns", "desc": "Microservices vs monoliths, SOLID principles, Creational/Structural/Behavioral Gang of Four patterns (Factory, Observer, Strategy)."},
                    {"num": 4, "co": "CO4", "title": "Software Testing & Quality Assurance", "desc": "Unit testing, integration testing, boundary value analysis, equivalence partitioning, cyclomatic complexity, code coverage."},
                    {"num": 5, "co": "CO5", "title": "DevOps, CI/CD & Reliability Engineering", "desc": "Git workflows, automated build pipelines, container orchestration, blue-green deployments and SRE observability."}
                ]
            },
            {
                "code": "MA301",
                "name": "Discrete Mathematics & Graph Theory",
                "department": "Computer Science",
                "semester": 6,
                "credits": 3,
                "modules": [
                    {"num": 1, "co": "CO1", "title": "Mathematical Logic & Proof Techniques", "desc": "Propositional logic, truth tables, first-order predicate calculus, direct proofs, contraposition, induction and contradiction."},
                    {"num": 2, "co": "CO2", "title": "Sets, Relations & Functions", "desc": "Equivalence relations, partial orderings, Hasse diagrams, lattices, bijective mappings and Cardinality."},
                    {"num": 3, "co": "CO3", "title": "Combinatorics & Recurrence Relations", "desc": "Permutations, combinations, Pigeonhole Principle, inclusion-exclusion, generating functions and linear homogeneous recurrences."},
                    {"num": 4, "co": "CO4", "title": "Graph Theory & Connectivity", "desc": "Eulerian and Hamiltonian graphs, planar graphs, Kuratowski's theorem, vertex coloring, chromatic number and tree traversals."},
                    {"num": 5, "co": "CO5", "title": "Algebraic Structures & Group Theory", "desc": "Semigroups, monoids, groups, subgroups, Lagrange's Theorem, rings, fields and modular arithmetic in cryptography."}
                ]
            }
        ]

        subject_entities = {}
        for s_data in subjects_data:
            subj = Subject(
                code=s_data["code"],
                name=s_data["name"],
                department=s_data["department"],
                semester=s_data["semester"],
                credits=s_data["credits"]
            )
            session.add(subj)
            await session.flush()
            subject_entities[s_data["code"]] = {"subject": subj, "modules": {}}

            for m_data in s_data["modules"]:
                mod = SubjectModule(
                    subject_id=subj.id,
                    module_number=m_data["num"],
                    co_code=m_data["co"],
                    title=m_data["title"],
                    description=m_data["desc"]
                )
                session.add(mod)
                await session.flush()
                subject_entities[s_data["code"]]["modules"][m_data["co"]] = mod

        # -------------------------------------------------------------
        # 3. Enroll All 10 Students in all 6 Subjects
        # -------------------------------------------------------------
        for email, st in student_objs:
            for s_code, s_info in subject_entities.items():
                enr = StudentEnrollment(
                    student_id=st.id,
                    subject_id=s_info["subject"].id,
                    semester=6,
                    academic_year="2025-2026"
                )
                session.add(enr)
        await session.flush()

        # -------------------------------------------------------------
        # 4. Create 5 Assessments per Subject (CA1, CA2, CA3, Midterm, Endterm)
        # -------------------------------------------------------------
        assessments_config = [
            {
                "category": "CA1",
                "name": "Continuous Assessment 1",
                "max_marks": 20.0,
                "weightage_pct": 10.0,
                "date": "2026-01-28",
                "questions": [
                    {"label": "Q1", "co": "CO1", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q2", "co": "CO1", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q3.a", "co": "CO2", "max": 5.0, "opt": True, "or_grp": "CA1-Q3-OR"},
                    {"label": "Q3.b", "co": "CO2", "max": 5.0, "opt": True, "or_grp": "CA1-Q3-OR"},
                    {"label": "Q4", "co": "CO2", "max": 5.0, "opt": False, "or_grp": None}
                ]
            },
            {
                "category": "CA2",
                "name": "Continuous Assessment 2",
                "max_marks": 20.0,
                "weightage_pct": 10.0,
                "date": "2026-02-25",
                "questions": [
                    {"label": "Q1", "co": "CO2", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q2", "co": "CO3", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q3.a", "co": "CO3", "max": 5.0, "opt": True, "or_grp": "CA2-Q3-OR"},
                    {"label": "Q3.b", "co": "CO3", "max": 5.0, "opt": True, "or_grp": "CA2-Q3-OR"},
                    {"label": "Q4", "co": "CO3", "max": 5.0, "opt": False, "or_grp": None}
                ]
            },
            {
                "category": "CA3",
                "name": "Continuous Assessment 3",
                "max_marks": 20.0,
                "weightage_pct": 10.0,
                "date": "2026-03-24",
                "questions": [
                    {"label": "Q1", "co": "CO4", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q2", "co": "CO4", "max": 5.0, "opt": False, "or_grp": None},
                    {"label": "Q3.a", "co": "CO5", "max": 5.0, "opt": True, "or_grp": "CA3-Q3-OR"},
                    {"label": "Q3.b", "co": "CO5", "max": 5.0, "opt": True, "or_grp": "CA3-Q3-OR"},
                    {"label": "Q4", "co": "CO5", "max": 5.0, "opt": False, "or_grp": None}
                ]
            },
            {
                "category": "Midterm",
                "name": "Mid-Semester Examination",
                "max_marks": 50.0,
                "weightage_pct": 20.0,
                "date": "2026-02-15",
                "questions": [
                    {"label": "Q1.a", "co": "CO1", "max": 10.0, "opt": False, "or_grp": None},
                    {"label": "Q2.a", "co": "CO2", "max": 10.0, "opt": False, "or_grp": None},
                    {"label": "Q3.a", "co": "CO3", "max": 10.0, "opt": True, "or_grp": "MID-Q3-OR"},
                    {"label": "Q3.b", "co": "CO3", "max": 10.0, "opt": True, "or_grp": "MID-Q3-OR"},
                    {"label": "Q4.a", "co": "CO1", "max": 10.0, "opt": False, "or_grp": None},
                    {"label": "Q5.a", "co": "CO2", "max": 10.0, "opt": False, "or_grp": None}
                ]
            },
            {
                "category": "Endterm",
                "name": "End-Semester Examination",
                "max_marks": 100.0,
                "weightage_pct": 50.0,
                "date": "2026-04-30",
                "questions": [
                    {"label": "Q1", "co": "CO1", "max": 20.0, "opt": False, "or_grp": None},
                    {"label": "Q2", "co": "CO2", "max": 20.0, "opt": False, "or_grp": None},
                    {"label": "Q3.a", "co": "CO3", "max": 20.0, "opt": True, "or_grp": "END-Q3-OR"},
                    {"label": "Q3.b", "co": "CO3", "max": 20.0, "opt": True, "or_grp": "END-Q3-OR"},
                    {"label": "Q4", "co": "CO4", "max": 20.0, "opt": False, "or_grp": None},
                    {"label": "Q5", "co": "CO5", "max": 20.0, "opt": False, "or_grp": None}
                ]
            }
        ]

        jane_target_pcts = {
            "CS301": {"CO1": 0.82, "CO2": 0.78, "CO3": 0.42, "CO4": 0.70, "CO5": 0.65},
            "CS302": {"CO1": 0.94, "CO2": 0.92, "CO3": 0.88, "CO4": 0.55, "CO5": 0.80},
            "CS303": {"CO1": 0.84, "CO2": 0.80, "CO3": 0.48, "CO4": 0.74, "CO5": 0.72},
            "CS304": {"CO1": 0.88, "CO2": 0.52, "CO3": 0.92, "CO4": 0.78, "CO5": 0.75},
            "CS305": {"CO1": 0.90, "CO2": 0.88, "CO3": 0.92, "CO4": 0.85, "CO5": 0.86},
            "MA301": {"CO1": 0.80, "CO2": 0.78, "CO3": 0.82, "CO4": 0.45, "CO5": 0.70}
        }

        student_proficiencies = {
            "alex@campus.edu": 0.75,
            "maya.lin@campus.edu": 0.91,
            "liam.chen@campus.edu": 0.68,
            "priya.sharma@campus.edu": 0.87,
            "carlos.r@campus.edu": 0.62,
            "aisha.p@campus.edu": 0.84,
            "david.kim@campus.edu": 0.79,
            "elena.rossi@campus.edu": 0.71,
            "marcus.vance@campus.edu": 0.65
        }

        for s_code, s_info in subject_entities.items():
            subj = s_info["subject"]
            modules_map = s_info["modules"]

            for a_cfg in assessments_config:
                assessment = Assessment(
                    subject_id=subj.id,
                    category=a_cfg["category"],
                    name=f"{subj.code} {a_cfg['name']}",
                    max_marks=a_cfg["max_marks"],
                    weightage_pct=a_cfg["weightage_pct"],
                    assessment_date=a_cfg["date"]
                )
                session.add(assessment)
                await session.flush()

                question_entities = []
                for q_cfg in a_cfg["questions"]:
                    mod = modules_map.get(q_cfg["co"])
                    q_entity = AssessmentQuestion(
                        assessment_id=assessment.id,
                        module_id=mod.id if mod else None,
                        co_code=q_cfg["co"],
                        question_label=q_cfg["label"],
                        max_marks=q_cfg["max"],
                        is_optional=q_cfg["opt"],
                        or_group_id=q_cfg["or_grp"]
                    )
                    session.add(q_entity)
                    await session.flush()
                    question_entities.append((q_cfg, q_entity))

                for email, student in student_objs:
                    is_jane = (email == "student@campus.edu")

                    for q_cfg, q_entity in question_entities:
                        co = q_cfg["co"]
                        max_m = q_cfg["max"]
                        is_or_choice = q_cfg["opt"]

                        if is_or_choice:
                            if q_cfg["label"].endswith(".b") or "b" in q_cfg["label"]:
                                mark = StudentQuestionMark(
                                    student_id=student.id,
                                    question_id=q_entity.id,
                                    marks_obtained=0.0,
                                    is_attempted=False,
                                    feedback="Optional question not chosen."
                                )
                                session.add(mark)
                                continue

                        if is_jane:
                            # Exact calibrated marks for CS301 to match verified baseline
                            cs301_exact_marks = {
                                ("CA1", "Q1"): 4.2, ("CA1", "Q2"): 4.2, ("CA1", "Q3.a"): 4.0, ("CA1", "Q4"): 4.0,
                                ("CA2", "Q1"): 4.0, ("CA2", "Q2"): 1.8, ("CA2", "Q3.a"): 1.8, ("CA2", "Q4"): 1.8,
                                ("CA3", "Q1"): 3.6, ("CA3", "Q2"): 3.6, ("CA3", "Q3.a"): 3.4, ("CA3", "Q4"): 3.4,
                                ("Midterm", "Q1.a"): 8.5, ("Midterm", "Q2.a"): 7.9, ("Midterm", "Q3.a"): 3.8, ("Midterm", "Q4.a"): 8.5, ("Midterm", "Q5.a"): 7.9,
                                ("Endterm", "Q1"): 17.0, ("Endterm", "Q2"): 15.9, ("Endterm", "Q3.a"): 7.9, ("Endterm", "Q4"): 14.2, ("Endterm", "Q5"): 13.6
                            }

                            if s_code == "CS301" and (a_cfg["category"], q_cfg["label"]) in cs301_exact_marks:
                                marks_obtained = cs301_exact_marks[(a_cfg["category"], q_cfg["label"])]
                            else:
                                target_ratio = jane_target_pcts[s_code].get(co, 0.70)
                                var_factor = ((hash(q_cfg["label"] + s_code) % 7) - 3) * 0.02
                                final_ratio = max(0.15, min(0.98, target_ratio + var_factor))
                                marks_obtained = round(max_m * final_ratio, 1)
                            
                            feedback = None
                            target_ratio = jane_target_pcts[s_code].get(co, 0.70)
                            if target_ratio < 0.50:
                                feedback = f"Needs improvement in {co} concepts: check lecture notes and micro-lesson."
                            elif target_ratio >= 0.85:
                                feedback = f"Excellent mastery of {co} analytical methods."
                            else:
                                feedback = "Good attempt. Review edge cases and notation."
                        else:
                            base_prof = student_proficiencies.get(email, 0.70)
                            hash_mod = ((hash(email + s_code + co) % 15) - 7) * 0.02
                            final_ratio = max(0.20, min(0.98, base_prof + hash_mod))
                            marks_obtained = round(max_m * final_ratio, 1)
                            feedback = "Graded based on standard rubric."

                        mark = StudentQuestionMark(
                            student_id=student.id,
                            question_id=q_entity.id,
                            marks_obtained=marks_obtained,
                            is_attempted=True,
                            feedback=feedback
                        )
                        session.add(mark)

        await session.flush()

        # -------------------------------------------------------------
        # 5. Seed Comprehensive Multi-Page Learning Materials (All 6 Subjects)
        # -------------------------------------------------------------
        materials_data = [
            # 1. CS301 - Operating Systems (CO1 to CO5)
            {
                "subject_code": "CS301",
                "co_code": "CO1",
                "title": "OS Module 1: Process Lifecycle, Concurrency & POSIX Threads",
                "source": "NexuxEdu Courseware / CS301 Operating Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Process Control Block (PCB) & Context Switching",
                        "content": (
                            "A Process is a program in execution. The operating system represents each process via a Process Control Block (PCB).\n"
                            "The PCB contains the Process ID (PID), program counter, CPU registers, memory limits, and open file descriptors.\n"
                            "Context Switching is the computational mechanism where the CPU saves state of the currently executing process "
                            "into its PCB and restores the state of another ready process. It represents pure CPU overhead."
                        ),
                        "topics": [
                            {"name": "PCB and Context Switch Overhead", "text": "The PCB stores register state and PID. Context switching saves/restores PCB state and incurs memory cache invalidation overhead."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Threads & Inter-Process Communication (IPC)",
                        "content": (
                            "A Thread is a basic unit of CPU utilization sharing address space, code, and data with peer threads, while having "
                            "its own stack and registers. POSIX pthread_create() spawns kernel threads.\n"
                            "IPC Mechanisms:\n"
                            "1. Shared Memory: Fastest IPC, requires synchronization locks.\n"
                            "2. Message Passing: Direct or indirect via mailboxes (pipes, sockets, message queues)."
                        ),
                        "topics": [
                            {"name": "Multithreading and IPC Paradigms", "text": "Threads share process virtual address space but have independent stacks. IPC uses shared memory or kernel message queues."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS301",
                "co_code": "CO2",
                "title": "OS Module 2: CPU Scheduling & Banker's Deadlock Avoidance",
                "source": "NexuxEdu Courseware / CS301 Operating Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "CPU Scheduling Algorithms (Round Robin vs SJF)",
                        "content": (
                            "CPU scheduling allocates CPU cores among ready queue processes.\n"
                            "- Shortest Job First (SJF): Provably minimal average waiting time, requires burst time prediction.\n"
                            "- Round Robin (RR): Preemptive, assigns time quantum 'q'. If q is large -> FCFS; if q is too small -> excessive context switch overhead.\n"
                            "- Multilevel Feedback Queue (MLFQ): Dynamically prioritizes I/O bound jobs and demotes CPU-intensive jobs."
                        ),
                        "topics": [
                            {"name": "CPU Scheduling Algorithms (SJF, RR, MLFQ)", "text": "SJF minimizes average wait time. Round Robin provides fair time-slicing bounded by quantum size."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Deadlock Avoidance & Banker's Safety Algorithm",
                        "content": (
                            "Deadlocks require 4 Coffman conditions: Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait.\n"
                            "Banker's Algorithm tests for safe states before granting resource allocation requests.\n"
                            "Safety Vector: Work = Available; Finish[i] = False.\n"
                            "Find process i such that Finish[i] == False and Need[i] <= Work.\n"
                            "Set Work = Work + Allocation[i], Finish[i] = True. If all Finish[i] == True -> System is SAFE."
                        ),
                        "topics": [
                            {"name": "Banker's Deadlock Avoidance Algorithm", "text": "Banker's algorithm ensures resource allocation never enters an unsafe state where deadlock could occur."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS301",
                "co_code": "CO3",
                "title": "OS Module 3: Virtual Memory Architecture, Paging & TLB Translation",
                "source": "NexuxEdu Courseware / CS301 Operating Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Memory Virtualization & Physical Address Spaces",
                        "content": (
                            "Memory virtualization provides each process with the illusion of an isolated, contiguous address space.\n"
                            "The CPU generates logical (virtual) addresses, which the Memory Management Unit (MMU) translates into "
                            "physical memory addresses at hardware speed using base/limit registers or page tables.\n\n"
                            "Key Advantages:\n"
                            "1. Process Isolation: No process can read or overwrite another process's physical memory.\n"
                            "2. Non-contiguous Allocation: Physical frames can be scattered across RAM while appearing continuous in virtual memory.\n"
                            "3. Over-allocation: Virtual memory size can exceed total installed physical RAM via demand paging to disk swap."
                        ),
                        "topics": [
                            {"name": "Virtual Memory Foundations", "text": "Virtual memory abstracts physical RAM into contiguous process address spaces managed by the MMU with hardware protection."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Paging Mechanics & Page Table Organization",
                        "content": (
                            "In a paging system, the virtual address space is divided into fixed-size units called 'Pages', and physical memory "
                            "is divided into equal-sized 'Frames' (commonly 4 KB = 2^12 bytes).\n\n"
                            "Virtual Address Format (32-bit architecture with 4 KB pages):\n"
                            "- Page Number (p): Upper 20 bits (determines index into Page Table).\n"
                            "- Offset (d): Lower 12 bits (identifies the byte within the 4 KB frame).\n\n"
                            "Page Table Entry (PTE) Flags:\n"
                            "- Frame Number: Physical frame index.\n"
                            "- Present/Valid Bit: 1 if frame is resident in RAM, 0 if on secondary storage (triggers Page Fault).\n"
                            "- Dirty/Modified Bit: 1 if page was written to (requires writeback to swap upon eviction).\n"
                            "- Read/Write & User/Kernel Protection Bits."
                        ),
                        "topics": [
                            {"name": "Paging and Page Tables", "text": "A virtual address splits into Page Number and Offset. The Page Table translates Page Number to Frame Number with Valid and Dirty status bits."}
                        ]
                    },
                    {
                        "page_number": 3,
                        "title": "Translation Lookaside Buffer (TLB) & Effective Access Time",
                        "content": (
                            "Accessing the page table in RAM for every memory instruction introduces a 100% memory access latency penalty (2 RAM lookups per read/write).\n"
                            "The Translation Lookaside Buffer (TLB) is an on-chip, highly associative hardware cache holding the most recent Page-to-Frame translations.\n\n"
                            "TLB Lookup Cycle:\n"
                            "1. CPU generates virtual address (p, d).\n"
                            "2. Parallel TLB search for page 'p'.\n"
                            "3. If TLB Hit: Hardware immediately concatenates frame 'f' with offset 'd' -> 1 RAM access.\n"
                            "4. If TLB Miss: MMU reads page table in RAM, loads mapping into TLB, then accesses data -> 2 RAM accesses.\n\n"
                            "Effective Access Time (EAT) Formula:\n"
                            "EAT = (Hit_Ratio * (TLB_Time + RAM_Time)) + ((1 - Hit_Ratio) * (TLB_Time + 2 * RAM_Time))\n"
                            "Example: If TLB_Time = 10ns, RAM_Time = 100ns, and Hit_Ratio = 90% (0.90):\n"
                            "EAT = (0.90 * 110ns) + (0.10 * 210ns) = 99ns + 21ns = 120ns."
                        ),
                        "topics": [
                            {"name": "TLB Hit/Miss & Effective Access Time (EAT)", "text": "The TLB is an associative cache for page translations. EAT formula: EAT = Hit_Ratio*(TLB+RAM) + (1-Hit_Ratio)*(TLB+2*RAM)."}
                        ]
                    },
                    {
                        "page_number": 4,
                        "title": "Page Fault Handling & Demand Paging",
                        "content": (
                            "When a process accesses a virtual page whose Present Bit is 0, the MMU raises a hardware interrupt known as a Page Fault.\n\n"
                            "Page Fault Handling Sequence:\n"
                            "1. Hardware Trap: Execution traps to the OS kernel page fault handler.\n"
                            "2. Legality Check: OS verifies if virtual address is valid in the process memory map.\n"
                            "3. Free Frame Search: OS locates a free physical frame (or selects a victim frame via page replacement).\n"
                            "4. Disk I/O: OS initiates disk read to fetch missing page into the allocated frame.\n"
                            "5. Table Update: OS sets frame number in Page Table and marks Present Bit = 1.\n"
                            "6. Instruction Restart: CPU resumes the exact instruction that faulted."
                        ),
                        "topics": [
                            {"name": "Page Fault Handling Lifecycle", "text": "Page fault occurs when present bit is 0. OS traps, finds free frame, loads page from disk swap, updates page table, and restarts instruction."}
                        ]
                    },
                    {
                        "page_number": 5,
                        "title": "Page Replacement Algorithms: FIFO, Optimal & LRU",
                        "content": (
                            "When physical RAM is full and a page fault occurs, the OS must choose a victim frame to evict.\n\n"
                            "1. FIFO (First-In, First-Out): Replaces oldest loaded page. Suffers from Belady's Anomaly (more frames can lead to more faults).\n"
                            "2. Optimal (MIN / Belady's Algorithm): Replaces page that will not be used for longest future time. Unattainable in practice, used as benchmark.\n"
                            "3. Least Recently Used (LRU): Replaces page that has not been accessed for longest time in past. Approximates Optimal using reference bits or stack aging.\n"
                            "4. Clock / Second-Chance Algorithm: Uses circular list and single reference bit to approximate LRU with low overhead."
                        ),
                        "topics": [
                            {"name": "Page Replacement Algorithms (FIFO, LRU, Optimal)", "text": "FIFO evicts oldest page, Optimal evicts longest unused in future, LRU evicts longest unused in past. Clock algorithm provides efficient LRU approximation."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS301",
                "co_code": "CO4",
                "title": "OS Module 4: Disk Scheduling & Inode File System Layouts",
                "source": "NexuxEdu Courseware / CS301 Operating Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Disk Arm Scheduling (SCAN, C-SCAN, LOOK)",
                        "content": (
                            "Disk I/O latency is dominated by Seek Time (moving the head to target cylinder).\n"
                            "- SSTF (Shortest Seek Time First): May starve requests far from arm.\n"
                            "- SCAN (Elevator): Arm moves in one direction servicing requests until the end, then reverses.\n"
                            "- C-SCAN (Circular SCAN): Moves in one direction servicing requests, then immediately returns to start without servicing on return, providing uniform wait times."
                        ),
                        "topics": [
                            {"name": "Disk Scheduling Algorithms (SCAN, C-SCAN)", "text": "SCAN and C-SCAN elevator algorithms minimize disk arm movement and eliminate SSTF starvation."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Unix Inode Architecture & File Allocation",
                        "content": (
                            "An Inode stores file metadata (size, owner, permissions) and block pointers:\n"
                            "- 12 Direct Pointers: Point directly to data blocks.\n"
                            "- 1 Singly Indirect Pointer: Points to a block containing pointers.\n"
                            "- 1 Doubly Indirect Pointer: Points to singly indirect blocks.\n"
                            "- 1 Triply Indirect Pointer: Supports multi-terabyte files efficiently."
                        ),
                        "topics": [
                            {"name": "Unix Inode Block Addressing", "text": "Inodes use direct, singly indirect, doubly indirect, and triply indirect block pointers to scale file size limits."}
                        ]
                    }
                ]
            },

            # 2. CS302 - Database Management Systems (CO1 to CO5)
            {
                "subject_code": "CS302",
                "co_code": "CO3",
                "title": "DBMS Module 3: Schema Refinement, Functional Dependencies & Normal Forms",
                "source": "NexuxEdu Courseware / CS302 Database Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Functional Dependencies & Closure of Attributes",
                        "content": (
                            "A Functional Dependency (FD) X -> Y asserts that whenever two tuples agree on attribute set X, they must agree on Y.\n"
                            "Attribute Closure X+ is the complete set of attributes functionally determined by X under a set of FDs F.\n\n"
                            "Algorithm for X+:\n"
                            "1. Initialize X+ = X.\n"
                            "2. Repeat until no change: If there is an FD A -> B in F such that A subset of X+, then X+ = X+ union B.\n"
                            "Candidate Key Definition: K is a superkey if K+ contains all attributes of relation R. K is a Candidate Key if it is minimal."
                        ),
                        "topics": [
                            {"name": "Functional Dependencies & Attribute Closure", "text": "An FD X -> Y specifies value determinism. Attribute closure X+ calculates all reachable attributes to identify candidate keys."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Normal Forms: 1NF, 2NF, 3NF and BCNF",
                        "content": (
                            "Normalization eliminates redundant data and prevents Insertion, Update, and Deletion anomalies.\n\n"
                            "- 1NF: All attribute values must be atomic (no multi-valued or composite attributes).\n"
                            "- 2NF: In 1NF and no non-prime attribute is partially dependent on any candidate key (full functional dependency).\n"
                            "- 3NF: In 2NF and for every non-trivial FD X -> A, either X is a superkey OR A is a prime attribute (no transitive dependencies).\n"
                            "- BCNF (Boyce-Codd Normal Form): For every non-trivial FD X -> A, X MUST BE a superkey. BCNF strictly eliminates all functional redundancy."
                        ),
                        "topics": [
                            {"name": "Database Normal Forms (1NF to BCNF)", "text": "1NF requires atomic values, 2NF removes partial key dependencies, 3NF eliminates transitive dependencies, BCNF requires every determinant to be a superkey."}
                        ]
                    },
                    {
                        "page_number": 3,
                        "title": "Lossless Join Decomposition & Dependency Preservation",
                        "content": (
                            "When decomposing relation R into R1 and R2:\n"
                            "1. Lossless Join: R1 join R2 must produce exactly R without spurious tuples. Condition: (R1 intersect R2) -> R1 OR (R1 intersect R2) -> R2.\n"
                            "2. Dependency Preservation: The union of projected FDs on R1 and R2 must imply all original FDs F.\n"
                            "Trade-off Note: Any relation can be decomposed into 3NF while guaranteeing BOTH lossless join and dependency preservation. BCNF guarantees lossless join, but dependency preservation is not always achievable."
                        ),
                        "topics": [
                            {"name": "Lossless Decomposition and Dependency Preservation", "text": "Decomposition is lossless if intersection of schemas is a superkey of at least one schema. 3NF guarantees dependency preservation whereas BCNF may not."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS302",
                "co_code": "CO4",
                "title": "DBMS Module 4: Transaction Concurrency & Two-Phase Locking (2PL)",
                "source": "NexuxEdu Courseware / CS302 Database Systems (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "ACID Properties & Conflict Serializability",
                        "content": (
                            "A Transaction is a logical unit of database work obeying ACID properties: Atomicity, Consistency, Isolation, Durability.\n"
                            "Conflict Serializability: A schedule S is conflict serializable if its Precedence (Serialization) Graph contains no cycles.\n"
                            "Two operations conflict if they belong to different transactions, access the same data item, and at least one is a Write."
                        ),
                        "topics": [
                            {"name": "ACID Properties and Conflict Serializability", "text": "Conflict serializability is verified via precedence graphs. Two operations conflict if one is a write on the same item by different transactions."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Two-Phase Locking (2PL) & Deadlock Handling",
                        "content": (
                            "Two-Phase Locking (2PL) Protocol guarantees Conflict Serializability:\n"
                            "1. Growing Phase: Transaction may acquire locks (Shared S or Exclusive X), but cannot release any.\n"
                            "2. Shrinking Phase: Transaction may release locks, but cannot acquire any new locks.\n"
                            "Strict 2PL: All exclusive locks are held until transaction Commit/Abort, preventing cascading aborts."
                        ),
                        "topics": [
                            {"name": "Two-Phase Locking Protocol (2PL)", "text": "2PL enforces growing and shrinking lock phases to ensure serializability. Strict 2PL holds exclusive locks until commit."}
                        ]
                    }
                ]
            },

            # 3. CS303 - Computer Networks (CO1 to CO5)
            {
                "subject_code": "CS303",
                "co_code": "CO3",
                "title": "Networks Module 3: Routing Protocols, CIDR & Dijkstra Shortest Path",
                "source": "NexuxEdu Courseware / CS303 Computer Networks (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "IP Subnetting, CIDR & Variable Length Subnet Masking",
                        "content": (
                            "Classless Inter-Domain Routing (CIDR) uses prefix notation (e.g. 192.168.1.0/24) to replace rigid Class A/B/C boundaries.\n"
                            "Given /26 subnet: 32 - 26 = 6 host bits -> 2^6 = 64 total IP addresses (62 usable host IPs, 1 network ID, 1 broadcast ID).\n\n"
                            "Longest Prefix Match Rule:\n"
                            "When forwarding a packet, the router selects the routing table entry with the most specific (longest) subnet mask matching the destination IP."
                        ),
                        "topics": [
                            {"name": "CIDR Subnetting and Longest Prefix Match", "text": "CIDR notation /N specifies network prefix length. Usable hosts = 2^(32-N) - 2. Routers forward packets using Longest Prefix Match."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Dijkstra's Link-State Routing Algorithm",
                        "content": (
                            "In Link-State Routing (e.g., OSPF), every node floods link-state packets (LSPs) so all routers construct an identical network topology graph.\n"
                            "Each router independently executes Dijkstra's algorithm to compute shortest paths from itself (root) to all other nodes.\n\n"
                            "Dijkstra Algorithm Steps:\n"
                            "1. Set distance d(s) = 0 for source s, and d(v) = infinity for all other nodes. Set Visited = {}\n"
                            "2. While Visited != All Nodes:\n"
                            "   a. Select unvisited node u with minimum distance d(u).\n"
                            "   b. Add u to Visited.\n"
                            "   c. For each unvisited neighbor v of u: d(v) = min(d(v), d(u) + weight(u, v)).\n"
                            "3. Build shortest path tree and populate routing forwarding table."
                        ),
                        "topics": [
                            {"name": "Dijkstra's Shortest Path Routing", "text": "Link-state routing uses Dijkstra's greedy algorithm with min-priority queues to compute optimal shortest paths across full topology graphs."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS303",
                "co_code": "CO4",
                "title": "Networks Module 4: TCP Handshake, Flow & Congestion Control",
                "source": "NexuxEdu Courseware / CS303 Computer Networks (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "TCP 3-Way Handshake & Sliding Window Flow Control",
                        "content": (
                            "TCP provides reliable byte-stream transport using a 3-Way Handshake (SYN, SYN-ACK, ACK).\n"
                            "Flow Control: The receiver advertises its available buffer space in the Receive Window (rwnd) field. "
                            "Sender ensures unacknowledged bytes never exceed rwnd to prevent receiver buffer overflow."
                        ),
                        "topics": [
                            {"name": "TCP Handshake and Flow Control", "text": "TCP 3-way handshake initializes sequence numbers. Flow control throttles sender transmission according to receiver rwnd."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "TCP Reno & Cubic Congestion Control",
                        "content": (
                            "Congestion Control manages network bottleneck capacity via Congestion Window (cwnd):\n"
                            "1. Slow Start: cwnd doubles every RTT until slow start threshold (ssthresh) is reached.\n"
                            "2. Congestion Avoidance: cwnd grows linearly (+1 MSS per RTT).\n"
                            "3. Fast Retransmit & Recovery: Triggered by 3 duplicate ACKs -> sets ssthresh = cwnd / 2 and retransmits immediately without waiting for RTO timer."
                        ),
                        "topics": [
                            {"name": "TCP Congestion Control (Slow Start, Fast Recovery)", "text": "TCP uses AIMD (additive increase, multiplicative decrease) with Slow Start and Fast Retransmit to prevent network collapse."}
                        ]
                    }
                ]
            },

            # 4. CS304 - Algorithms (CO1 to CO5)
            {
                "subject_code": "CS304",
                "co_code": "CO2",
                "title": "Algorithms Module 2: Dynamic Programming & Optimal Substructure",
                "source": "NexuxEdu Courseware / CS304 Design & Analysis of Algorithms (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Dynamic Programming Principles: Memoization vs Tabulation",
                        "content": (
                            "Dynamic Programming solves problems with Overlapping Subproblems and Optimal Substructure.\n"
                            "- Top-Down (Memoization): Recursive approach with lookup table caching results.\n"
                            "- Bottom-Up (Tabulation): Iterative approach filling table in dependency order, saving call stack overhead."
                        ),
                        "topics": [
                            {"name": "Dynamic Programming Paradigms", "text": "DP combines optimal substructure with memoization (top-down) or tabulation (bottom-up) to eliminate exponential recomputation."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "0/1 Knapsack Problem Formulation",
                        "content": (
                            "Given N items with weights w[i] and values v[i], and Knapsack capacity W:\n"
                            "DP State: dp[i][w] is max value achievable using subset of first i items within weight limit w.\n"
                            "Recurrence:\n"
                            "dp[i][w] = dp[i-1][w] if w[i] > w\n"
                            "dp[i][w] = max(dp[i-1][w], v[i] + dp[i-1][w - w[i]]) otherwise.\n"
                            "Time Complexity: O(N * W) (Pseudo-polynomial time)."
                        ),
                        "topics": [
                            {"name": "0/1 Knapsack DP Recurrence", "text": "0/1 Knapsack solves item inclusion decisions in O(NW) table space using optimal subproblem states."}
                        ]
                    }
                ]
            },
            {
                "subject_code": "CS304",
                "co_code": "CO3",
                "title": "Algorithms Module 3: Balanced Search Trees & AVL Rotations",
                "source": "NexuxEdu Courseware / CS304 Design & Analysis of Algorithms (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "AVL Trees, Balance Factor & Rotation Types",
                        "content": (
                            "An AVL Tree is a strictly self-balancing Binary Search Tree where the Balance Factor (BF) of every node satisfies:\n"
                            "Balance Factor (BF) = Height(Left_Subtree) - Height(Right_Subtree) in {-1, 0, +1}.\n"
                            "If an insertion or deletion causes |BF| > 1, the tree performs single or double rotations to restore balance in O(1) time.\n\n"
                            "Four Imbalance Cases:\n"
                            "1. Left-Left (LL): Inserted in left subtree of left child -> Fixed by Single Right Rotation.\n"
                            "2. Right-Right (RR): Inserted in right subtree of right child -> Fixed by Single Left Rotation.\n"
                            "3. Left-Right (LR): Inserted in right subtree of left child -> Fixed by Left Rotation on child, then Right Rotation on node.\n"
                            "4. Right-Left (RL): Inserted in left subtree of right child -> Fixed by Right Rotation on child, then Left Rotation on node."
                        ),
                        "topics": [
                            {"name": "AVL Tree Rotations and Invariants", "text": "AVL trees maintain balance factor in {-1, 0, 1}. Violations are resolved via LL (Right Rotate), RR (Left Rotate), LR (Left-Right), or RL (Right-Left) rotations."}
                        ]
                    }
                ]
            },

            # 5. CS305 - Software Engineering (CO1 to CO5)
            {
                "subject_code": "CS305",
                "co_code": "CO3",
                "title": "Software Engineering Module 3: Architectural Patterns & SOLID Principles",
                "source": "NexuxEdu Courseware / CS305 Software Engineering & Architecture (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "SOLID Object-Oriented Design Principles",
                        "content": (
                            "SOLID Principles for maintainable software:\n"
                            "- S: Single Responsibility Principle (A class should have only one reason to change).\n"
                            "- O: Open/Closed Principle (Open for extension, closed for modification).\n"
                            "- L: Liskov Substitution Principle (Derived classes must be substitutable for base classes).\n"
                            "- I: Interface Segregation Principle (Clients should not depend on interfaces they do not use).\n"
                            "- D: Dependency Inversion Principle (Depend on abstractions, not concretions)."
                        ),
                        "topics": [
                            {"name": "SOLID Architectural Design Principles", "text": "SOLID principles guide decoupled, extensible object-oriented component boundaries."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "GoF Design Patterns (Factory, Observer, Strategy)",
                        "content": (
                            "Gang of Four (GoF) Patterns:\n"
                            "- Factory Pattern (Creational): Creates objects without specifying exact concrete class.\n"
                            "- Observer Pattern (Behavioral): Defines 1-to-N dependency where subject notifies all observers on state change.\n"
                            "- Strategy Pattern (Behavioral): Encapsulates interchangeable algorithms behind a common interface."
                        ),
                        "topics": [
                            {"name": "Gang of Four Software Patterns", "text": "Factory, Observer, and Strategy patterns provide standard decoupled blueprints for object creation and behavior."}
                        ]
                    }
                ]
            },

            # 6. MA301 - Discrete Mathematics (CO1 to CO5)
            {
                "subject_code": "MA301",
                "co_code": "CO4",
                "title": "Discrete Math Module 4: Graph Theory, Planarity & Trees",
                "source": "NexuxEdu Courseware / MA301 Discrete Mathematics (Synthetic Demo Data)",
                "pages": [
                    {
                        "page_number": 1,
                        "title": "Eulerian & Hamiltonian Paths and Circuits",
                        "content": (
                            "- Eulerian Trail: Visits every edge exactly once. Exists in connected graph if and only if 0 or 2 vertices have odd degree.\n"
                            "- Eulerian Circuit: Eulerian trail that starts and ends at same vertex. Exists if and only if EVERY vertex has even degree.\n"
                            "- Hamiltonian Path: Visits every vertex exactly once. Determining Hamiltonian existence is NP-complete."
                        ),
                        "topics": [
                            {"name": "Eulerian and Hamiltonian Graph Properties", "text": "Eulerian graphs require even vertex degrees. Hamiltonian graphs visit every vertex once and are NP-complete to decide."}
                        ]
                    },
                    {
                        "page_number": 2,
                        "title": "Planar Graphs & Euler's Formula",
                        "content": (
                            "A Planar Graph can be drawn in a plane without intersecting edges.\n"
                            "Euler's Formula for connected planar graph: V - E + F = 2 (where V=vertices, E=edges, F=faces).\n"
                            "Kuratowski's Theorem: A graph is planar if and only if it contains no subgraph homeomorphic to K5 (complete graph on 5 vertices) or K3,3 (utility graph)."
                        ),
                        "topics": [
                            {"name": "Planar Graphs and Kuratowski's Theorem", "text": "Planar graphs obey Euler's formula V - E + F = 2 and contain no K5 or K3,3 minors."}
                        ]
                    }
                ]
            }
        ]

        for mat_data in materials_data:
            s_code = mat_data["subject_code"]
            subj = subject_entities[s_code]["subject"]
            mod = subject_entities[s_code]["modules"].get(mat_data["co_code"])

            mat = LearningMaterial(
                subject_id=subj.id,
                module_id=mod.id if mod else None,
                title=mat_data["title"],
                source_reference=mat_data["source"],
                total_pages=len(mat_data["pages"])
            )
            session.add(mat)
            await session.flush()

            for p_data in mat_data["pages"]:
                page = MaterialPage(
                    material_id=mat.id,
                    page_number=p_data["page_number"],
                    page_title=p_data["title"],
                    content_text=p_data["content"],
                    structured_json=json.dumps({"topics": [t["name"] for t in p_data["topics"]]})
                )
                session.add(page)
                await session.flush()

                for idx, t_data in enumerate(p_data["topics"]):
                    emb_vec = generate_pseudo_embedding(t_data["name"] + " " + t_data["text"])
                    chunk = MaterialChunk(
                        material_id=mat.id,
                        page_id=page.id,
                        module_id=mod.id if mod else None,
                        co_code=mat_data["co_code"],
                        topic_name=t_data["name"],
                        chunk_index=idx,
                        chunk_text=t_data["text"],
                        embedding_json=json.dumps(emb_vec)
                    )
                    session.add(chunk)

        await session.flush()

        # -------------------------------------------------------------
        # 6. Seed Declarative JSON Micro-Lessons for Interactive Player
        # -------------------------------------------------------------
        micro_lessons_data = [
            {
                "subject_code": "CS301",
                "co_code": "CO3",
                "topic_key": "os_memory_paging_tlb",
                "title": "Demystifying Paging, Page Tables & The TLB Hit/Miss Cycle",
                "duration": 180,
                "scenes": [
                    {
                        "scene_id": 1,
                        "title": "The Memory Virtualization Illusion",
                        "duration_seconds": 35,
                        "narration": "Modern operating systems give every process its own private, isolated virtual address space. But physical RAM is shared. How does the CPU translate virtual addresses into actual memory cells instantly?",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "Virtual to Physical Address Translation",
                            "ascii_diagram": (
                                "+-------------------------------------------+\n"
                                "|   Process Virtual Address (32-bit)        |\n"
                                "|   [ Page Number: p ] [ Offset: d (12b) ]  |\n"
                                "+---------------------+---------------------+\n"
                                "                      | (Lookup in Page Table)\n"
                                "                      v\n"
                                "+-------------------------------------------+\n"
                                "|   Page Table Entry: Frame Number 'f'      |\n"
                                "+---------------------+---------------------+\n"
                                "                      | (Concatenate)\n"
                                "                      v\n"
                                "+-------------------------------------------+\n"
                                "|   Physical Address: [ Frame: f ] [ Off: d]|\n"
                                "+-------------------------------------------+"
                            ),
                            "highlights": ["Page Number indexes the Page Table", "Offset (12 bits = 4KB page) remains identical in physical memory"]
                        },
                        "key_takeaway": "Virtual addresses split into Page Number and Offset; the MMU maps Page Number to Frame Number."
                    },
                    {
                        "scene_id": 2,
                        "title": "The Problem: Double Memory Access Latency",
                        "duration_seconds": 35,
                        "narration": "Because the page table itself lives in main RAM, every single memory read or write requires TWO memory accesses: one to read the page table, and one to read the actual data. This cuts system speed in half!",
                        "visual_type": "table",
                        "visual_data": {
                            "columns": ["Access Step", "Location", "Latency Penalty"],
                            "rows": [
                                ["1. Lookup PTE", "Main Memory (RAM)", "+100 ns"],
                                ["2. Fetch Byte", "Main Memory (RAM)", "+100 ns"],
                                ["Total Without TLB", "2 x RAM Latency", "200 ns (100% overhead)"]
                            ]
                        },
                        "key_takeaway": "Without hardware acceleration, paging doubles every single memory access time."
                    },
                    {
                        "scene_id": 3,
                        "title": "The Hero: Translation Lookaside Buffer (TLB)",
                        "duration_seconds": 45,
                        "narration": "To eliminate this bottleneck, CPUs use a Translation Lookaside Buffer (TLB)—a lightning-fast hardware cache of recent translations. On a TLB Hit, translation takes only ~1 nanosecond!",
                        "visual_type": "flowchart",
                        "visual_data": {
                            "steps": [
                                "1. CPU emits Virtual Address (p, d)",
                                "2. MMU checks TLB in parallel (Fast on-chip cache)",
                                "3. TLB HIT -> Frame 'f' found -> Access RAM directly (Total ~100ns)",
                                "4. TLB MISS -> Access Page Table in RAM -> Load PTE into TLB -> Access RAM (Total ~200ns)"
                            ]
                        },
                        "key_takeaway": "TLB caches active Page-to-Frame mappings on the CPU chip to avoid redundant RAM lookups."
                    },
                    {
                        "scene_id": 4,
                        "title": "Mastering the Effective Access Time (EAT) Formula",
                        "duration_seconds": 40,
                        "narration": "In exams, you calculate Effective Access Time using the weighted hit-miss formula. With a 95% TLB hit ratio, access time is nearly identical to raw hardware speed.",
                        "visual_type": "code",
                        "visual_data": {
                            "language": "python",
                            "code_snippet": (
                                "# Effective Access Time (EAT) Calculation\n"
                                "hit_ratio = 0.95      # 95% TLB Hit Rate\n"
                                "tlb_time = 10         # 10 ns lookup\n"
                                "ram_time = 100        # 100 ns RAM latency\n\n"
                                "# Formula: Hit Cost + Miss Cost\n"
                                "eat = (hit_ratio * (tlb_time + ram_time)) + \\\n"
                                "      ((1 - hit_ratio) * (tlb_time + 2 * ram_time))\n\n"
                                "print(f'EAT = {eat} ns') # -> 115.0 ns"
                            )
                        },
                        "key_takeaway": "EAT = Hit_Ratio * (TLB + RAM) + (1 - Hit_Ratio) * (TLB + 2 * RAM)."
                    },
                    {
                        "scene_id": 5,
                        "title": "Quick Knowledge Check",
                        "duration_seconds": 25,
                        "narration": "Let's test your understanding. If a 32-bit architecture uses 4 KB pages, how many bits are used for the Page Offset?",
                        "visual_type": "step_by_step",
                        "visual_data": {
                            "question": "What is the offset bit width for a 4 KB page size?",
                            "options": ["A. 10 bits (1024 bytes)", "B. 12 bits (2^12 = 4096 bytes)", "C. 16 bits (65536 bytes)"],
                            "correct_answer": "B. 12 bits",
                            "explanation": "4 KB = 4096 bytes = 2^12. Therefore, the lowest 12 bits of the virtual address represent the byte offset 'd'."
                        },
                        "key_takeaway": "Page size = 2^(offset bits). For 4 KB pages, offset is always 12 bits."
                    }
                ],
                "video_path": "lessons/cs301_co3_os_memory_paging_tlb.mp4",
                "video_status": "ready",
                "youtube_resource": {
                    "video_id": "p3q5BIzRsmU",
                    "title": "Lecture 17: Virtual Memory & Page Translation",
                    "channel": "MIT OpenCourseWare",
                    "start_seconds": 120,
                    "end_seconds": 480,
                    "description": "Comprehensive visual walkthrough of page table lookup mechanics, multi-level hierarchy, and TLB caching acceleration."
                }
            },
            {
                "subject_code": "CS301",
                "co_code": "CO3",
                "topic_key": "os_virtual_memory_page_replacement",
                "title": "Virtual Memory: Page Faults & LRU Replacement Mechanics",
                "duration": 180,
                "scenes": [
                    {
                        "scene_id": 1,
                        "title": "When Memory Runs Out: The Page Fault",
                        "duration_seconds": 35,
                        "narration": "When a thread touches a virtual page marked 'Not Present', the CPU raises a Page Fault interrupt. The OS must load that page from disk swap. But what if RAM has no free frames?",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "Page Fault Interrupt Handling",
                            "ascii_diagram": (
                                "CPU Access -> Page Table (Present Bit = 0) -> TRAP to OS Kernel\n"
                                "                                                |\n"
                                "                                                v\n"
                                "RAM Full? -> Select Victim Frame via LRU -> Evict to Swap -> Load Missing Page"
                            )
                        },
                        "key_takeaway": "Page Faults trigger kernel intervention to fetch pages from secondary storage into RAM."
                    },
                    {
                        "scene_id": 2,
                        "title": "The Least Recently Used (LRU) Strategy",
                        "duration_seconds": 45,
                        "narration": "LRU selects the frame that has not been referenced for the longest period in the past. It assumes past access patterns predict future temporal locality.",
                        "visual_type": "table",
                        "visual_data": {
                            "columns": ["Reference String", "Frame 1", "Frame 2", "Frame 3", "Fault Status"],
                            "rows": [
                                ["Page 7", "7", "-", "-", "FAULT"],
                                ["Page 0", "7", "0", "-", "FAULT"],
                                ["Page 1", "7", "0", "1", "FAULT"],
                                ["Page 2", "2 (Evicts 7)", "0", "1", "FAULT (7 was LRU)"],
                                ["Page 0", "2", "0 (Hit)", "1", "HIT (0 now newest)"],
                                ["Page 3", "2", "0", "3 (Evicts 1)", "FAULT (1 was LRU)"]
                            ]
                        },
                        "key_takeaway": "LRU evicts the page with the oldest timestamp of last access."
                    },
                    {
                        "scene_id": 3,
                        "title": "Belady's Anomaly & The FIFO Pitfall",
                        "duration_seconds": 40,
                        "narration": "Beware of FIFO! Under FIFO page replacement, giving a process MORE frames can actually INCREASE page faults. This is known as Belady's Anomaly. LRU is a stack algorithm and is mathematically immune to Belady's Anomaly.",
                        "visual_type": "flowchart",
                        "visual_data": {
                            "steps": [
                                "FIFO with 3 frames on sequence [1,2,3,4,1,2,5,1,2,3,4,5] -> 9 Faults",
                                "FIFO with 4 frames on SAME sequence -> 10 Faults (Anomaly!)",
                                "LRU is a Stack Algorithm -> Increasing frames NEVER increases faults."
                            ]
                        },
                        "key_takeaway": "FIFO suffers from Belady's Anomaly; LRU is a stack algorithm and never experiences it."
                    }
                ],
                "video_path": "lessons/cs301_co3_os_virtual_memory_page_replacement.mp4",
                "video_status": "ready",
                "youtube_resource": {
                    "video_id": "dYBLfgV1f6c",
                    "title": "Page Replacement Algorithms: FIFO, LRU, Optimal",
                    "channel": "Gate Smashers",
                    "start_seconds": 30,
                    "end_seconds": 420,
                    "description": "Step-by-step trace of frame allocation, LRU stack implementation, and mathematical proof of Belady's anomaly."
                }
            },
            {
                "subject_code": "CS302",
                "co_code": "CO3",
                "topic_key": "dbms_normalization_bcnf",
                "title": "Decomposing to Boyce-Codd Normal Form (BCNF) Without Data Loss",
                "duration": 180,
                "scenes": [
                    {
                        "scene_id": 1,
                        "title": "Why Normalization Matters",
                        "duration_seconds": 35,
                        "narration": "Poor database schema design leads to redundant storage and dangerous anomalies. If a student enrolls in a course, should changing the professor's office location require updating 500 rows?",
                        "visual_type": "table",
                        "visual_data": {
                            "columns": ["StudentID", "Course", "Professor", "Office"],
                            "rows": [
                                ["101", "CS301", "Dr. Turing", "Room 402"],
                                ["102", "CS301", "Dr. Turing", "Room 402 (Redundant)"],
                                ["103", "CS301", "Dr. Turing", "Room 402 (Update Anomaly Risk)"]
                            ]
                        },
                        "key_takeaway": "Functional dependencies identify redundant columns that should be split into distinct relations."
                    },
                    {
                        "scene_id": 2,
                        "title": "The Golden Rule of BCNF",
                        "duration_seconds": 45,
                        "narration": "A schema is in Boyce-Codd Normal Form (BCNF) if and only if for EVERY non-trivial functional dependency X -> Y, the left side X is a Superkey. If X is not a superkey, the table MUST be decomposed.",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "BCNF Verification Invariant",
                            "ascii_diagram": (
                                "Given Relation R(A, B, C, D) and FD: A -> B\n"
                                "1. Calculate Attribute Closure of A: A+ = {A, B}\n"
                                "2. Is A+ equal to all attributes {A, B, C, D}? NO -> A is not a Superkey!\n"
                                "3. BCNF VIOLATION! Decompose R into R1(A, B) and R2(A, C, D)."
                            )
                        },
                        "key_takeaway": "BCNF requires every determinant (left hand side of FD) to be a superkey."
                    },
                    {
                        "scene_id": 3,
                        "title": "Guaranteeing Lossless Join Decomposition",
                        "duration_seconds": 45,
                        "narration": "When splitting relation R into R1 and R2, you must ensure you can join them back without creating fake phantom rows. The intersection of R1 and R2 must be a superkey of at least one of them.",
                        "visual_type": "step_by_step",
                        "visual_data": {
                            "steps": [
                                "Check: (R1 intersect R2) -> R1  OR  (R1 intersect R2) -> R2",
                                "If intersection is a superkey of R1 -> Decomposition is 100% Lossless",
                                "Never decompose on attributes that share no functional key relationship."
                            ]
                        },
                        "key_takeaway": "Lossless join is guaranteed when the shared attributes form a superkey of at least one sub-relation."
                    }
                ],
                "video_path": "lessons/cs302_co3_dbms_normalization_bcnf.mp4",
                "video_status": "ready",
                "youtube_resource": {
                    "video_id": "UrYLYV7WSHM",
                    "title": "Boyce-Codd Normal Form (BCNF) Decomposition",
                    "channel": "NPTEL IIT Kharagpur",
                    "start_seconds": 45,
                    "end_seconds": 390,
                    "description": "Determining candidate keys, identifying non-trivial functional dependencies, and lossless BCNF decomposition."
                }
            },
            {
                "subject_code": "CS304",
                "co_code": "CO3",
                "topic_key": "algo_avl_rotations",
                "title": "Mastering AVL Tree Self-Balancing Rotations (LL, RR, LR, RL)",
                "duration": 180,
                "scenes": [
                    {
                        "scene_id": 1,
                        "title": "The AVL Balance Invariant",
                        "duration_seconds": 35,
                        "narration": "Binary search trees can degenerate into O(n) linked lists if inserted in sorted order. AVL trees prevent this by enforcing that the height difference between left and right subtrees is at most 1.",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "Balance Factor Definition",
                            "ascii_diagram": (
                                "Balance Factor (BF) = Height(Left_Child) - Height(Right_Child)\n"
                                "Valid BF Values: {-1, 0, +1}\n"
                                "If BF becomes +2 or -2 -> Immediate Tree Rotation Required!"
                            )
                        },
                        "key_takeaway": "AVL trees guarantee O(log n) search, insert, and delete by maintaining Balance Factor in {-1, 0, +1}."
                    },
                    {
                        "scene_id": 2,
                        "title": "Single Rotations: Left-Left & Right-Right",
                        "duration_seconds": 45,
                        "narration": "When an insertion happens in the outside subtree, a single rotation fixes it. An insertion into the Left-Left path causes a +2 balance, solved by a Single Right Rotation.",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "Single Right Rotation (LL Case)",
                            "ascii_diagram": (
                                "     z (BF=+2)                     y (BF=0)\n"
                                "    /                             / \\\n"
                                "   y (BF=+1)   -- Right Rotate ->x   z\n"
                                "  / \n"
                                " x"
                            )
                        },
                        "key_takeaway": "LL imbalance is resolved by a single Right Rotation; RR imbalance is resolved by a single Left Rotation."
                    },
                    {
                        "scene_id": 3,
                        "title": "Double Rotations: Left-Right & Right-Left",
                        "duration_seconds": 45,
                        "narration": "When insertion happens on an inside branch (like Left-Right 'zigzag'), a single rotation fails. You must first rotate the child Left to convert it to an LL line, then rotate the parent Right!",
                        "visual_type": "flowchart",
                        "visual_data": {
                            "steps": [
                                "1. Detect LR Imbalance: Parent BF = +2, Left Child BF = -1 (Zigzag)",
                                "2. Step 1: Left Rotate on Left Child (Converts LR into LL)",
                                "3. Step 2: Right Rotate on Parent Node (Restores Balance Factor to 0)"
                            ]
                        },
                        "key_takeaway": "LR imbalance requires a Left-Rotate on child followed by a Right-Rotate on parent."
                    }
                ],
                "video_path": "lessons/cs304_co3_algo_avl_rotations.mp4",
                "video_status": "ready",
                "youtube_resource": {
                    "video_id": "jDM6_TnYIqE",
                    "title": "AVL Tree - Insertion and Rotations (LL, RR, LR, RL)",
                    "channel": "Abdul Bari",
                    "start_seconds": 60,
                    "end_seconds": 540,
                    "description": "Visual intuition behind balance factors, single line rotations, and double zigzag rotations in self-balancing trees."
                }
            },
            {
                "subject_code": "CS303",
                "co_code": "CO3",
                "topic_key": "net_dijkstra_routing",
                "title": "Link-State Routing & Step-by-Step Dijkstra Shortest Path",
                "duration": 180,
                "scenes": [
                    {
                        "scene_id": 1,
                        "title": "How Routers Map the Global Internet",
                        "duration_seconds": 35,
                        "narration": "In link-state routing protocols like OSPF, every router broadcasts its immediate link costs to the entire network. Soon, every router possesses an identical global map.",
                        "visual_type": "diagram",
                        "visual_data": {
                            "diagram_title": "Link-State Topology Flooding",
                            "ascii_diagram": (
                                "Router A --(1)-- Router B --(3)-- Router C\n"
                                "    \\                               /\n"
                                "     +------------(6)--------------+"
                            )
                        },
                        "key_takeaway": "Link-state flooding gives every router a complete map of the network graph."
                    },
                    {
                        "scene_id": 2,
                        "title": "Executing Dijkstra's Greedy Algorithm",
                        "duration_seconds": 50,
                        "narration": "Starting from itself, the router maintains tentative distances to all nodes. At each step, it permanently locks the closest unvisited node and relaxes all of its outgoing links.",
                        "visual_type": "table",
                        "visual_data": {
                            "columns": ["Step", "Locked Node", "Tentative Dist to B", "Tentative Dist to C"],
                            "rows": [
                                ["Init", "A (Dist 0)", "1 via A", "6 via A"],
                                ["Step 1", "B (Dist 1)", "LOCKED", "min(6, 1+3) = 4 via B"],
                                ["Step 2", "C (Dist 4)", "LOCKED", "LOCKED (Shortest path is A->B->C cost 4)"]
                            ]
                        },
                        "key_takeaway": "Dijkstra locks minimum tentative distance node and relaxes neighbor edges until all nodes are visited."
                    }
                ],
                "video_path": "lessons/cs303_co3_net_dijkstra_routing.mp4",
                "video_status": "ready",
                "youtube_resource": {
                    "video_id": "XB4MIexjvY0",
                    "title": "Dijkstra's Shortest Path Algorithm - Graph Theory",
                    "channel": "Computerphile",
                    "start_seconds": 15,
                    "end_seconds": 360,
                    "description": "How link-state routing protocols compute optimal forwarding paths using priority queues and greedy relaxation."
                }
            }
        ]

        for ml_data in micro_lessons_data:
            s_code = ml_data["subject_code"]
            subj = subject_entities[s_code]["subject"]
            mod = subject_entities[s_code]["modules"].get(ml_data["co_code"])

            total_scenes_duration = sum(s.get("duration_seconds", 0) for s in ml_data["scenes"])
            yt_res = ml_data.get("youtube_resource")
            lesson = MicroLesson(
                subject_id=subj.id,
                module_id=mod.id if mod else None,
                co_code=ml_data["co_code"],
                topic_key=ml_data["topic_key"],
                title=ml_data["title"],
                duration_seconds=total_scenes_duration or ml_data.get("duration", 180),
                scenes_json=json.dumps(ml_data["scenes"]),
                video_path=ml_data.get("video_path"),
                video_status=ml_data.get("video_status", "none"),
                video_duration=total_scenes_duration or ml_data.get("duration", 180),
                youtube_resource_json=json.dumps(yt_res) if yt_res else None
            )
            session.add(lesson)

        await session.commit()
        print("Enriched Academic Support data successfully seeded with 6 subjects, 30 modules, 30 assessments, student marks, materials, and micro-lessons!")

if __name__ == "__main__":
    import asyncio
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    asyncio.run(seed_academic_support_data(force_reseed=True))
