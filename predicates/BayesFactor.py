import numpy as np
import scipy.stats as st
from sklearn.metrics import f1_score
from rpy2.robjects import Formula
from rpy2.robjects.packages import importr
from rpy2.robjects import numpy2ri, pandas2ri
import rpy2.rinterface_lib.callbacks
import rpy2.robjects as robjects

numpy2ri.activate()
pandas2ri.activate()
RBayesFactor=importr('BayesFactor', suppress_messages=True)

class BayesFactor(object):
    
    def __call__(self, value, mask1, mask2=None, *args, **kwargs):
        mask2 = ~mask1 if mask2 is None else mask2
        return self.bayes_factor(value[mask1], value[mask2], *args, **kwargs)
    
class JZS(BayesFactor):
    
    def __init__(self, side=None, rscale='medium'):
        self.side = side
        self.rscale = rscale
    
    def bayes_factor(self, value1, value2, return_samples=False):
        if self.side == 'right' and value1.mean() < value2.mean():
            bf = -100000
        elif self.side == 'left' and value1.mean() < value2.mean():
            bf = -100000
        elif len(value1)>1 and len(value2)>2:
            res = RBayesFactor.ttestBF(x=value1, y=value2, rscale=self.rscale)
            bf = res.slots['bayesFactor']['bf'][0]
        else:
            bf = -100000
        if return_samples:
            return bf, (None, None, None)
        else:
            return bf
    
class Anomaly(BayesFactor):
    
    def __init__(self, num_samples=1000):
        self.num_samples = num_samples
    
    def bayes_factor(self, value1, value2, return_dist=False):
        if len(value1) == 0:
            bf = -np.inf
            mean = 0
            std = 1
            mean_ = 0
            prec_ = 1
            dist = None
        else:
            a = value2.count()
            b = value2.sum()
            mean = b/a
            std = np.sqrt(b)/a

            prec = 100
            prec_ = prec*value1.count()
            mean_ = value1.mean()

            dist = st.norm(mean_ - mean, std + np.sqrt(1/prec_))
            l1 = dist.logsf(0)
            l2 = dist.logcdf(0)
            bf = l1 - l2
        if return_dist:
            return bf, (st.norm(mean, std), st.norm(mean_, np.sqrt(1/prec_)), dist)
        else:
            return bf
        
class F1(object):
    
    def __call__(self, value, mask, *args, **kwargs):
        return f1_score(value, mask), None