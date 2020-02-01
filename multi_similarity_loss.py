import tensorflow as tf


def ms_loss(
        labels,
        embeddings,
        alpha=2.0,
        beta=50.0,
        lamb=1.0,
        eps=0.1,
        ms_mining=False):
    '''
    ref: http://openaccess.thecvf.com/content_CVPR_2019/papers/Wang_Multi-Similarity_Loss_With_General_Pair_Weighting_for_Deep_Metric_Learning_CVPR_2019_paper.pdf
    official pytorch codes: https://github.com/MalongTech/research-ms-loss
    original tensorflow 1.x code: https://github.com/geonm/tf_ms_loss/blob/master/tf_ms_loss.py
    '''
    labels = tf.reshape(labels, [-1, 1])
    batch_size = tf.size(labels)
    adjacency = tf.equal(labels, tf.transpose(labels))
    adjacency_not = tf.logical_not(adjacency)
    mask_pos = tf.cast(adjacency, dtype=tf.float32) - \
        tf.eye(batch_size, dtype=tf.float32)
    mask_neg = tf.cast(adjacency_not, dtype=tf.float32)

    sim_mat = tf.matmul(
        embeddings,
        embeddings,
        transpose_a=False,
        transpose_b=True)
    sim_mat = tf.maximum(sim_mat, 0.0)

    pos_mat = tf.multiply(sim_mat, mask_pos)
    neg_mat = tf.multiply(sim_mat, mask_neg)

    if ms_mining:
        max_val = tf.reduce_max(neg_mat, axis=1, keepdims=True)
        tmp_max_val = tf.reduce_max(pos_mat, axis=1, keepdims=True)
        min_val = tf.reduce_min(
            tf.multiply(
                sim_mat - tmp_max_val,
                mask_pos),
            axis=1,
            keepdims=True) + tmp_max_val

        max_val = tf.tile(max_val, [1, batch_size])
        min_val = tf.tile(min_val, [1, batch_size])

        mask_pos = tf.where(
            pos_mat < max_val + eps,
            mask_pos,
            tf.zeros_like(mask_pos))
        mask_neg = tf.where(
            neg_mat > min_val - eps,
            mask_neg,
            tf.zeros_like(mask_neg))

    pos_exp = tf.exp(-alpha * (pos_mat - lamb))
    pos_exp = tf.where(mask_pos > 0.0, pos_exp, tf.zeros_like(pos_exp))

    neg_exp = tf.exp(beta * (neg_mat - lamb))
    neg_exp = tf.where(mask_neg > 0.0, neg_exp, tf.zeros_like(neg_exp))

    pos_term = tf.math.log(1.0 + tf.reduce_sum(pos_exp, axis=1)) / alpha
    neg_term = tf.math.log(1.0 + tf.reduce_sum(neg_exp, axis=1)) / beta

    loss = tf.reduce_mean(pos_term + neg_term)
    return loss


class MultiSimilarityLoss(tf.keras.losses.Loss):

    def __init__(
            self,
            alpha=2.0,
            beta=50.0,
            lamb=1.0,
            eps=0.1,
            ms_mining=False,
            name=None):

        super().__init__(name=name)
        self.alpha = alpha
        self.beta = beta
        self.lamb = lamb
        self.eps = eps
        self.ms_mining = ms_mining

    def call(self, y_true, y_pred):
        return ms_loss(
            y_true,
            y_pred,
            self.alpha,
            self.beta,
            self.lamb,
            self.eps,
            self.ms_mining)
