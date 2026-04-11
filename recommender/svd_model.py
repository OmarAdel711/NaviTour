"""
Pure Python SVD — Collaborative Filtering
──────────────────────────────────────────
Implements Matrix Factorization (SVD-style) using only
Python's standard library (math, random, collections).

No NumPy. No scikit-surprise. No external dependencies.
Works on any Python 3.8+ environment.

Algorithm: Stochastic Gradient Descent Matrix Factorization
  R ≈ global_mean + bias_u + bias_i + P[u] · Q[i]
"""

import random
import logging
from math import sqrt
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Hyperparameters ───────────────────────────────────────────
N_FACTORS = 50
N_EPOCHS  = 30     # ← stop here, not 50
LR        = 0.005
REG       = 0.04   # ← stronger regularization prevents memorizing
RATING_MIN = 1.0
RATING_MAX = 5.0

# ── Model cache (train once per server start) ─────────────────
_model         = None
_trained_users = set()
_trained_items = set()


# ═══════════════════════════════════════════════════════════════
# Pure Python Matrix Factorization
# ═══════════════════════════════════════════════════════════════

class PureSVD:
    """
    Stochastic Gradient Descent Matrix Factorization.
    Predicts: r(u,i) = global_mean + bias_u + bias_i + P[u]·Q[i]
    """

    def __init__(self, n_factors=N_FACTORS, n_epochs=N_EPOCHS, lr=LR, reg=REG):
        self.n_factors   = n_factors
        self.n_epochs    = n_epochs
        self.lr          = lr
        self.reg         = reg
        self.global_mean = 3.5
        self.user_factors = {}
        self.item_factors = {}
        self.user_bias    = {}
        self.item_bias    = {}
        self.known_users  = set()
        self.known_items  = set()

    def _vec(self):
        return [random.gauss(0, 0.1) for _ in range(self.n_factors)]

    @staticmethod
    def _dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _clip(v):
        return max(RATING_MIN, min(RATING_MAX, v))

    def fit(self, ratings):
        """ratings: list of (user_id, item_id, rating) tuples"""
        if not ratings:
            return self

        random.seed(42)
        self.global_mean = sum(r for _, _, r in ratings) / len(ratings)
        self.known_users = {u for u, _, _ in ratings}
        self.known_items = {i for _, i, _ in ratings}

        for u in self.known_users:
            self.user_factors[u] = self._vec()
            self.user_bias[u]    = 0.0
        for i in self.known_items:
            self.item_factors[i] = self._vec()
            self.item_bias[i]    = 0.0

        lr, reg = self.lr, self.reg
        for epoch in range(self.n_epochs):
            random.shuffle(ratings)
            loss = 0.0
            for u, i, r in ratings:
                pred = (self.global_mean
                        + self.user_bias[u]
                        + self.item_bias[i]
                        + self._dot(self.user_factors[u], self.item_factors[i]))
                err   = r - pred
                loss += err * err

                self.user_bias[u] += lr * (err - reg * self.user_bias[u])
                self.item_bias[i] += lr * (err - reg * self.item_bias[i])

                pu = self.user_factors[u]
                qi = self.item_factors[i]
                for k in range(self.n_factors):
                    old_pu = pu[k]
                    pu[k] += lr * (err * qi[k]   - reg * pu[k])
                    qi[k] += lr * (err * old_pu  - reg * qi[k])

            if (epoch + 1) % 5 == 0:
                logger.info(f"  Epoch {epoch+1:2d}/{self.n_epochs}  RMSE={sqrt(loss/len(ratings)):.4f}")

        return self

    def predict(self, user_id, item_id) -> float:
        ub = self.user_bias.get(user_id, 0.0)
        ib = self.item_bias.get(item_id, 0.0)
        pu = self.user_factors.get(user_id)
        qi = self.item_factors.get(item_id)
        if pu is None or qi is None:
            val = self.global_mean + ub + ib
        else:
            val = self.global_mean + ub + ib + self._dot(pu, qi)
        return round(self._clip(val), 3)


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def get_model(engine):
    global _model, _trained_users, _trained_items
    if _model is None:
        _model, _trained_users, _trained_items = _train(engine)
    return _model, _trained_users, _trained_items


def _train(engine):
    logger.info("Training SVD (pure Python, no dependencies)...")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT user_id,
                   place_type || '_' || place_id AS item_id,
                   CAST(rating AS FLOAT) AS rating
            FROM ratings
        """)).fetchall()

    if not rows:
        logger.warning("No ratings in DB — SVD skipped.")
        return None, set(), set()

    ratings = [(int(r[0]), str(r[1]), float(r[2])) for r in rows]
    model   = PureSVD().fit(ratings)

    trained_users = {u for u, _, _ in ratings}
    trained_items = {i for _, i, _ in ratings}
    logger.info(f"SVD ready: {len(trained_users)} users, "
                f"{len(trained_items)} items, "
                f"global_mean={model.global_mean:.2f}")
    return model, trained_users, trained_items


def predict(engine, user_id: int, place_type: str, place_id: int) -> float:
    """Predict rating user_id gives to (place_type, place_id). Returns [1,5]."""
    model, _, _ = get_model(engine)
    if model is None:
        return 3.5
    return model.predict(user_id, f"{place_type}_{place_id}")


def retrain(engine):
    """Force full retrain after new ratings are inserted."""
    global _model, _trained_users, _trained_items
    _model, _trained_users, _trained_items = _train(engine)
    logger.info("SVD retrained.")
