"""BM25 Okapi tối giản, không phụ thuộc thư viện ngoài.

Token hóa mặc định theo khoảng trắng: dùng được cho cả văn bản âm tiết
(chunks.csv) và văn bản đã tách từ (chunks_segmented.csv, từ ghép nối bằng _).
"""
import math
import re
from collections import Counter

from src.data.text_utils import normalize_tone


def tokenize(text):
    # Câu hỏi phải đc chuẩn hóa giống hệt kho dữ liệu
    #Kho đã thành hủy mà ng dùng gõ "huỷ" → ko khớp, nên cần chuẩn hóa
    # normalize_tone tự trả về NFC nên không cần gọi unicodedata.normalize("NFC") nữa;
    # vẫn cần lower() để BM25 không phân biệt hoa/thường
    text = normalize_tone(text).lower()
    return re.findall(r"\w+", text)


class BM25:
    def __init__(self, docs, ids, k1=1.5, b=0.75):
        self.ids = list(ids)
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens) if self.lens else 0.0
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(self.tfs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query):
        q = tokenize(query)
        out = []
        for tf, dl in zip(self.tfs, self.lens):
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return out

    def search(self, query, k=10):
        sc = self.scores(query)
        order = sorted(range(len(sc)), key=lambda i: sc[i], reverse=True)[:k]
        return [(self.ids[i], sc[i]) for i in order]
