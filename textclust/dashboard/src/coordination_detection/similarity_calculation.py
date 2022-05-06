from tqdm import tqdm
import numpy as np
from scipy.spatial.distance import squareform

# Function to create the pairwise similarities
# It is a function copied from scipy and adapted for the
# specific use case.
# Original implementation:
# https://github.com/scipy/scipy/blob/v1.2.3/scipy/spatial/distance.py#L1717-L2075
def pairwise_similarity_calculation(data, metric):
    if len(data.shape) != 2:
        raise ValueError('A 2-dimensional array must be passed.')

    data = np.asarray(data, order='c')
    m = data.shape[0]
    k = 0
    dm = np.empty((m * (m - 1)) // 2, dtype=np.double)

    for i in tqdm(range(0, m - 1)):
        for j in range(i + 1, m):
            dm[k] = metric(data[i], data[j])
            k = k + 1
    return squareform(dm)