from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------------
# Load Embedding Model
# -----------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------------
# Compute Semantic Similarity
# -----------------------------------
def compute_similarity(jd, resume):

    jd_emb = model.encode(
        [jd],
        normalize_embeddings=True
    )

    res_emb = model.encode(
        [resume],
        normalize_embeddings=True
    )

    score = cosine_similarity(jd_emb, res_emb)[0][0]

    return round(score * 100, 2)