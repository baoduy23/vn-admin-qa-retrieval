"""TF-IDF + cosine. Dùng giống BM25: TFIDF(docs, ids).search(query, k).

Token hoá dùng chung bm25.tokenize (normalize_tone, lower, tách theo \\w+), nên chạy được cả mức âm tiết
(chunk_text) lẫn mức từ (text_seg, từ ghép nối bằng _), và câu hỏi cũng được chuẩn hoá y như vậy.
"""
from sklearn.feature_extraction.text import TfidfVectorizer

from src.retrieval.bm25 import tokenize


class TFIDF:
    def __init__(self, docs, ids, ngram_range=(1, 2), sublinear_tf=True):
        self.ids = list(ids)
        # token_pattern=None, lowercase=False để tắt token hoá mặc định của sklearn, dùng tokenize của nhóm
        self.vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                   ngram_range=tuple(ngram_range), sublinear_tf=sublinear_tf)
        self.mat = self.vec.fit_transform(docs)          # mỗi dòng đã chuẩn hóa L2

    def scores(self, query):
        # vector đã chuẩn hoá L2 nên tích vô hướng chính là cosine
        return (self.mat @ self.vec.transform([query]).T).toarray().ravel().tolist()

    def search(self, query, k=10):
        sc = self.scores(query)
        order = sorted(range(len(sc)), key=lambda i: sc[i], reverse=True)[:k]
        return [(self.ids[i], sc[i]) for i in order]
