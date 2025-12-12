"""
Intent Classification Module
Detects user query type: General, Context Data, atau Interaction Data
Uses hybrid approach: ML-based semantic similarity + keyword fallback
"""

from typing import Tuple, List, Optional


# Small, fast local model from Hugging Face (22MB); works offline
LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class IntentClassifier:
    """Classify user intent using ML-based semantic similarity with keyword fallback"""

    # Cache for embeddings to avoid recomputing
    _embedding_cache = {}
    _local_model = None
    _local_model_failed = False
    _remote_failed = False

    # Training examples for each intent (for semantic matching)
    TRAINING_EXAMPLES = {
        "general": {
            "education": [
                "apa itu investasi?",
                "jelaskan tentang budgeting",
                "bagaimana cara menabung?",
                "tips mengatur keuangan",
                "strategi investasi untuk pemula",
                "what is compound interest?",
                "explain financial planning",
                "how to save money effectively",
            ],
            "greeting": [
                "halo",
                "hai, apa kabar?",
                "hello there",
                "good morning",
                "selamat pagi",
                "hi, how are you?",
            ],
            "help": [
                "bantuan",
                "apa yang bisa kamu lakukan?",
                "fitur apa saja yang tersedia?",
                "help me",
                "what can you do?",
                "show me features",
            ],
        },
        "context_data": {
            "summary": [
                "berapa total pengeluaran bulan ini?",
                "total pemasukan saya",
                "summary keuangan saya",
                "what is my balance?",
                "berapa saldo saya sekarang?",
                "show me financial overview",
                "laporan keuangan",
            ],
            "report": [
                "laporan pengeluaran minggu ini",
                "analisis trend keuangan saya",
                "show spending trends",
                "perbandingan bulan ini vs bulan lalu",
                "report my expenses",
            ],
            "retrieve": [
                "lihat transaksi terakhir",
                "tampilkan semua pengeluaran",
                "show my transactions",
                "cek saldo rekening",
                "daftar semua income saya",
            ],
        },
        "interaction_data": {
            "record": [
                "catat pengeluaran 50000 untuk makan",
                "saya habiskan 100rb untuk transport",
                "tambah pemasukan 5 juta dari gaji",
                "record expense Rp 75000 for groceries",
                "input income from freelance",
                "saya dapat uang 200rb dari bonus",
            ],
            "edit": [
                "ubah transaksi terakhir",
                "edit pengeluaran kemarin",
                "update amount to 150000",
                "ganti kategori ke entertainment",
                "perbaiki transaksi salah",
            ],
            "delete": [
                "hapus transaksi terakhir",
                "delete the expense I just added",
                "buang record yang salah",
                "remove transaction",
            ],
            "transfer": [
                "transfer 500rb dari cash ke bank",
                "pindahkan uang dari saving ke wallet",
                "move funds from account A to B",
            ],
            "goal": [
                "buat target menabung 10 juta",
                "set saving goal for vacation",
                "tujuan keuangan untuk beli laptop",
                "create accumulation goal",
            ],
        },
    }

    # Keywords untuk setiap kategori (fallback)
    GENERAL_KEYWORDS = {
        "education": [
            "apa itu",
            "jelaskan",
            "definisi",
            "bagaimana cara",
            "gimana cara",
            "tips",
            "strategi",
            "motivasi",
            "inspirasi",
            "pelajaran",
            "edukasi",
            "belajar",
            "understand",
            "explain",
            "definition",
            "how to",
            "tips",
            "strategy",
        ],
        "greeting": [
            "halo",
            "hai",
            "hello",
            "hi",
            "pagi",
            "siang",
            "malam",
            "good morning",
            "good afternoon",
        ],
        "help": [
            "bantuan",
            "help",
            "support",
            "fitur apa saja",
            "apa yang bisa",
            "bisa apa",
        ],
    }

    CONTEXT_DATA_KEYWORDS = {
        "summary": [
            "summary",
            "ringkasan",
            "total",
            "berapa",
            "berapa total",
            "total pengeluaran",
            "total pemasukan",
            "laporan",
            "report",
            "statistik",
            "stats",
            "overview",
        ],
        "report": [
            "laporan",
            "report",
            "analisis",
            "analysis",
            "trends",
            "trend",
            "perbandingan",
            "comparison",
            "ringkasan",
        ],
        "retrieve": [
            "lihat",
            "tampilkan",
            "show",
            "display",
            "cek",
            "check",
            "berapa saldo",
            "balance",
            "daftar",
            "list",
        ],
    }

    INTERACTION_DATA_KEYWORDS = {
        "record": [
            "catat",
            "record",
            "tambah",
            "add",
            "input",
            "buat",
            "create",
            "pemasukan",
            "pengeluaran",
            "income",
            "expense",
            "saya habiskan",
            "saya dapat",
            "saya terima",
            "i spent",
            "spent",
            "paid",
            "bought",
            "received",
            "earned",
            "got",
        ],
        "edit": [
            "ubah",
            "edit",
            "update",
            "ganti",
            "change",
            "perbaiki",
            "fix",
            "modify",
            "correct",
        ],
        "delete": [
            "hapus",
            "delete",
            "remove",
            "buang",
            "clear",
            "cancel",
        ],
        "transfer": [
            "transfer",
            "pindahkan",
            "move",
            "dari",
            "ke",
            "dari ... ke",
            "from",
            "to",
        ],
        "goal": [
            "target",
            "goal",
            "tujuan",
            "saving",
            "menabung",
            "akumulasi",
            "accumulate",
            "save for",
            "saving for",
            "want to save",
        ],
    }

    @staticmethod
    def _get_embedding(text: str) -> Optional[List[float]]:
        """Return embedding using local model first, then optional remote fallback."""
        if not text:
            return None

        # Cache hit
        if text in IntentClassifier._embedding_cache:
            return IntentClassifier._embedding_cache[text]

        # 1) Try local SentenceTransformer (offline)
        local_vec = IntentClassifier._get_embedding_local(text)
        if local_vec is not None:
            IntentClassifier._embedding_cache[text] = local_vec
            return local_vec

        # 2) Optional remote fallback (Gemini embeddings) if available
        remote_vec = IntentClassifier._get_embedding_remote(text)
        if remote_vec is not None:
            IntentClassifier._embedding_cache[text] = remote_vec
            return remote_vec

        return None

    @staticmethod
    def _get_embedding_local(text: str) -> Optional[List[float]]:
        """Generate embedding with a small offline model (no API calls)."""
        if IntentClassifier._local_model_failed:
            return None

        if text in IntentClassifier._embedding_cache:
            return IntentClassifier._embedding_cache[text]

        try:
            from sentence_transformers import SentenceTransformer

            if IntentClassifier._local_model is None:
                IntentClassifier._local_model = SentenceTransformer(LOCAL_MODEL_NAME)

            vec = IntentClassifier._local_model.encode(text, normalize_embeddings=True)
            # encode returns numpy array; convert to plain list for downstream use
            vec_list = vec.tolist() if hasattr(vec, "tolist") else list(vec)
            IntentClassifier._embedding_cache[text] = vec_list
            return vec_list
        except Exception as e:
            IntentClassifier._local_model_failed = True
            print(f"Local embedding unavailable: {e}")
            return None

    @staticmethod
    def _get_embedding_remote(text: str) -> Optional[List[float]]:
        """Optional remote embedding using Google Gemini if library + key exist."""
        if IntentClassifier._remote_failed:
            return None

        if text in IntentClassifier._embedding_cache:
            return IntentClassifier._embedding_cache[text]

        try:
            import importlib.util

            spec = importlib.util.find_spec("google.generativeai")
            if spec is None:
                IntentClassifier._remote_failed = True
                return None

            from config import GOOGLE_API_KEY

            if not GOOGLE_API_KEY:
                IntentClassifier._remote_failed = True
                return None

            genai = importlib.import_module("google.generativeai")
            genai.configure(api_key=GOOGLE_API_KEY)
            result = genai.embed_content(
                model="models/embedding-001", content=text, task_type="retrieval_query"
            )
            embedding = result.get("embedding")
            if embedding:
                IntentClassifier._embedding_cache[text] = embedding
            return embedding
        except Exception as e:
            IntentClassifier._remote_failed = True
            print(f"Remote embedding unavailable: {e}")
            return None

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def _classify_with_ml(query: str, backend: str = "local") -> Tuple[str, str, float]:
        """
        ML-based classification using semantic similarity.
        backend: "local" (HF) or "remote" (Gemini fallback)
        Returns: (category, intent_type, confidence)
        """
        embed_fn = (
            IntentClassifier._get_embedding_local
            if backend == "local"
            else IntentClassifier._get_embedding_remote
        )

        query_embedding = embed_fn(query)
        if query_embedding is None:
            return None, None, 0.0

        best_score = 0.0
        best_category = None
        best_type = None

        # Compare query with training examples
        for category, types in IntentClassifier.TRAINING_EXAMPLES.items():
            for intent_type, examples in types.items():
                for example in examples:
                    example_embedding = embed_fn(example)
                    if example_embedding:
                        similarity = IntentClassifier._cosine_similarity(
                            query_embedding, example_embedding
                        )

                        if similarity > best_score:
                            best_score = similarity
                            best_category = category
                            best_type = intent_type

        # Convert similarity score to confidence
        if best_score > 0.65:  # Strong match
            confidence = min(0.95, best_score)
        elif best_score > 0.5:  # Moderate match
            confidence = best_score * 0.85
        else:  # Weak match
            confidence = best_score * 0.5

        return best_category, best_type, confidence

    @staticmethod
    def classify(query: str) -> Tuple[str, str, float]:
        """
        Classify user query intent using hybrid ML + keyword approach.

        Returns:
            Tuple of (intent_category, intent_type, confidence)
            - intent_category: 'general', 'context_data', 'interaction_data'
            - intent_type: specific type like 'education', 'summary', 'record'
            - confidence: 0-1 score indicating how certain we are
        """
        query_lower = query.lower().strip()

        # 1) Primary: local HF embeddings
        local_cat, local_type, local_conf = IntentClassifier._classify_with_ml(
            query, backend="local"
        )

        # High confidence: return immediately
        if local_conf >= 0.7 and local_cat and local_type:
            return local_cat, local_type, local_conf

        # 2) Secondary: remote embeddings (Gemini) only if local is weak
        remote_cat, remote_type, remote_conf = (None, None, 0.0)
        if local_conf < 0.7:
            remote_cat, remote_type, remote_conf = IntentClassifier._classify_with_ml(
                query, backend="remote"
            )
            if remote_conf >= 0.7 and remote_cat and remote_type:
                return remote_cat, remote_type, remote_conf

        # 3) Fallback: keyword matching
        keyword_cat, keyword_type, keyword_conf = (
            IntentClassifier._classify_with_keywords(query_lower)
        )

        # Choose best among available signals
        candidates = [
            (local_conf, local_cat, local_type),
            (remote_conf, remote_cat, remote_type),
            (keyword_conf, keyword_cat, keyword_type),
        ]
        best = max(candidates, key=lambda x: x[0])
        return best[1], best[2], best[0]

    @staticmethod
    def _classify_with_keywords(query_lower: str) -> Tuple[str, str, float]:
        """Keyword-based classification (fallback method)"""

        # Use a more sophisticated matching approach
        # Track all matches with their confidence scores
        matches = []

        # Check Interaction Data (highest priority - most specific)
        for intent_type, keywords in IntentClassifier.INTERACTION_DATA_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    confidence = IntentClassifier._calculate_confidence(
                        query_lower, keyword
                    )
                    # Boost confidence for longer, more specific keywords
                    if len(keyword.split()) > 1:
                        confidence += 0.1
                    matches.append(
                        ("interaction_data", intent_type, confidence, len(keyword))
                    )

        # Check Context Data (medium priority)
        for intent_type, keywords in IntentClassifier.CONTEXT_DATA_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    confidence = IntentClassifier._calculate_confidence(
                        query_lower, keyword
                    )
                    if len(keyword.split()) > 1:
                        confidence += 0.1
                    matches.append(
                        ("context_data", intent_type, confidence, len(keyword))
                    )

        # Check General (lowest priority - fallback)
        for intent_type, keywords in IntentClassifier.GENERAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    confidence = IntentClassifier._calculate_confidence(
                        query_lower, keyword
                    )
                    if len(keyword.split()) > 1:
                        confidence += 0.1
                    matches.append(("general", intent_type, confidence, len(keyword)))

        # If we have matches, pick the best one
        # Sort by confidence first, then keyword length (more specific = longer keywords)
        if matches:
            matches.sort(key=lambda x: (x[2], x[3]), reverse=True)
            best = matches[0]
            return best[0], best[1], min(1.0, best[2])

        # No clear intent found - default to general with low confidence
        return "general", "unknown", 0.3

    @staticmethod
    def _calculate_confidence(query: str, matched_keyword: str) -> float:
        """Calculate confidence based on query characteristics"""
        confidence = 0.7  # Base confidence

        # Increase confidence if keyword is at start
        if query.startswith(matched_keyword):
            confidence += 0.2

        # Decrease confidence if query is very long (might be complex intent)
        if len(query.split()) > 15:
            confidence -= 0.1

        # Increase if query is direct/short
        if len(query.split()) <= 5:
            confidence += 0.1

        return min(1.0, max(0.0, confidence))

    @staticmethod
    def should_use_llm_fallback(confidence: float) -> bool:
        """Determine if we should fallback to LLM for intent clarification"""
        return confidence < 0.5
