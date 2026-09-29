"""
RAG Pipeline Implementation with Role-Based Retrieval-Time Filtering.

This module implements the `ERPRAGChatbot` class using LangChain, Ollama
(nomic-embed-text & llama3.2:3b), and ChromaDB. It enforces RBAC pre-retrieval
filtering so users never receive unauthorized context.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment configuration
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

try:
    from langchain.chains import RetrievalQA
except (ImportError, ModuleNotFoundError):
    from langchain_classic.chains import RetrievalQA

try:
    from .utils.rbac_filters import User, build_query_filters, describe_permissions
except ImportError:
    from utils.rbac_filters import User, build_query_filters, describe_permissions


# Custom prompt strictly commanding grounding and refusal of unauthorized data
SYSTEM_RAG_PROMPT_TEMPLATE = """You are the NexusEdu Educational ERP Assistant. Answer the user question using ONLY the verified context below.

Context:
{context}

Guidelines:
1. Answer the question directly, factually, and concisely using details present in the context above (e.g., student academic records, subjects, attendance, grades, faculty profiles, or bus/transit telemetry).
2. If the requested information is absent or not mentioned in the context above, respond strictly with: "Access to this information is forbidden."
3. Never guess, speculate, or reveal information outside the provided context.

Question: {question}
Answer:"""

RAG_PROMPT = PromptTemplate(
    template=SYSTEM_RAG_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)


class ERPRAGChatbot:
    """
    Educational ERP RAG Chatbot with Role-Based Access Control.
    
    Attributes:
        ollama_base_url (str): HTTP endpoint for local Ollama runtime.
        embedding_model (str): Name of embedding model (nomic-embed-text).
        chat_model (str): Name of LLM model (llama3.2:3b).
        persist_dir (str): Local filesystem path for ChromaDB storage.
        embeddings (OllamaEmbeddings): LangChain Ollama embeddings instance.
        llm (ChatOllama): LangChain Ollama chat LLM instance.
        vectorstore (Chroma): Persistent Chroma vector database.
    """

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        chat_model: Optional[str] = None,
        persist_dir: Optional[str] = None,
    ):
        self.ollama_base_url = ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "nomic-embed-text"
        )
        self.chat_model = chat_model or os.getenv("CHAT_MODEL", "llama3.2:3b")

        # Resolve persistent directory
        raw_persist_dir = persist_dir or os.getenv(
            "CHROMA_PERSIST_DIR", "./database/chroma_db"
        )
        if Path(raw_persist_dir).is_absolute():
            self.persist_dir = str(Path(raw_persist_dir))
        elif Path(raw_persist_dir).exists():
            self.persist_dir = str(Path(raw_persist_dir).resolve())
        else:
            self.persist_dir = str(
                (Path(__file__).resolve().parent / raw_persist_dir).resolve()
            )
        os.makedirs(self.persist_dir, exist_ok=True)

        # Initialize Ollama components
        self.embeddings = OllamaEmbeddings(
            base_url=self.ollama_base_url,
            model=self.embedding_model,
        )

        self.llm = ChatOllama(
            base_url=self.ollama_base_url,
            model=self.chat_model,
            temperature=0.0,  # Zero temperature for deterministic, factual grounding
        )

        # Initialize Chroma vector store
        self.collection_name = "erp_knowledge_base"
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir,
        )

    def initialize_database(self, documents: List[Document], clear_existing: bool = True):
        """
        Populates or rebuilds the ChromaDB vector store with chunked ERP documents.

        Args:
            documents (List[Document]): The extracted ERP document chunks.
            clear_existing (bool): If True, resets the existing vector store collection.
        """
        if not documents:
            print("[!] Warning: No documents provided to initialize_database.")
            return

        if clear_existing:
            print(f"[*] Resetting existing ChromaDB collection '{self.collection_name}'...")
            try:
                self.vectorstore.delete_collection()
            except Exception as e:
                # Collection might not exist yet
                pass

            # Re-instantiate clean collection
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )

        print(f"[*] Ingesting and embedding {len(documents)} ERP documents into ChromaDB...")
        # Add documents in batches for smooth memory utilization on 16GB RAM
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            self.vectorstore.add_documents(batch)
            print(f"    -> Embedded {min(i + batch_size, len(documents))}/{len(documents)} documents.")

        print(f"[+] Successfully populated ChromaDB index at: {self.persist_dir}")

    def create_chatbot(self, user: User) -> RetrievalQA:
        """
        Constructs a RetrievalQA chain configured with role-based filters applied to the retriever.

        Args:
            user (User): Authenticated user object containing role and security claims.

        Returns:
            RetrievalQA: An execution chain parameterized with the user's security boundaries.
        """
        filters = build_query_filters(user)

        search_kwargs: Dict[str, Any] = {"k": 4}
        if filters:
            search_kwargs["filter"] = filters

        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)

        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": RAG_PROMPT},
            return_source_documents=True,
        )
        return qa_chain

    def query(
        self,
        user: User,
        question: str,
        extra_docs: Optional[List[Document]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a role-filtered RAG query for an authenticated user.

        Args:
            user (User): Authenticated user object.
            question (str): The natural language query.
            extra_docs (Optional[List[Document]]): Additional verified runtime documents (e.g. live telematics).

        Returns:
            Dict[str, Any]: Contains 'answer', 'sources', 'filters_applied', and 'user_role'.
        """
        filters = build_query_filters(user)

        # 1. Retrieve candidate documents using RBAC filter
        search_kwargs: Dict[str, Any] = {"k": 4}
        if filters:
            search_kwargs["filter"] = filters

        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        retrieved_docs = retriever.invoke(question)

        all_docs = list(retrieved_docs)
        if extra_docs:
            all_docs.extend(extra_docs)

        # 2. Zero-Trust Context Grounding Check:
        # If RBAC filters out all documents, halt immediately and emit authorization refusal
        # without invoking the LLM. This saves compute and guarantees zero hallucination.
        if not all_docs:
            return {
                "answer": "Access to this information is forbidden.",
                "sources": [],
                "filters_applied": filters,
                "user_role": user.role,
                "retrieved_count": 0,
            }

        # 3. Direct RAG Synthesis with LLM using verified context
        context_str = "\n\n---\n\n".join(doc.page_content for doc in all_docs)
        formatted_prompt = RAG_PROMPT.format(context=context_str, question=question)
        llm_response = self.llm.invoke(formatted_prompt)
        answer = llm_response.content.strip()

        # Format source metadata for auditability
        sources = [
            {
                "chunk_id": doc.metadata.get("chunk_id", "unknown"),
                "entity_type": doc.metadata.get("entity_type", "unknown"),
                "sensitivity": doc.metadata.get("sensitivity", "unknown"),
            }
            for doc in all_docs
        ]

        return {
            "answer": answer,
            "sources": sources,
            "filters_applied": filters,
            "user_role": user.role,
            "retrieved_count": len(all_docs),
        }
