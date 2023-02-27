import pandas as pd
import numpy as np
import scipy.stats as st

class BayesFactor(object):
    
    def __call__(self, value, mask1, mask2=None, *args, **kwargs):
        mask2 = ~mask1 if mask2 is None else mask2
        return self.bayes_factor(value[mask1], value[mask2], *args, **kwargs)

class Anomaly(BayesFactor):
    
    def __init__(self, num_samples=1000):
        self.num_samples = num_samples
    
    def bayes_factor_(self, value1, value2, return_samples=False):
        alpha = value2.count()
        beta = value2.sum()
        norm_samples = pd.Series(np.random.gamma(beta, 1/alpha, size=self.num_samples))
        
        mean = value1.mean()
        prec = value1.count()*(1/value1.var())
        std = np.sqrt(1./prec)
        anom_samples = pd.Series(np.random.normal(mean, std, size=self.num_samples))
        p = (anom_samples>norm_samples).mean()
        if p == 1:
            bf = np.inf
        else:
            bf = p/(1-p)
        if return_samples:
            return bf, norm_samples, anom_samples
        else:
            return bf
        
    def bayes_factor(self, value1, value2):
        alpha = value2.count()
        beta = value2.sum()
        mean_ = beta/alpha
        std_ = beta/alpha**2
        
        mean = value1.mean()
        prec = value1.count()*(1/value1.var())
        std = np.sqrt(1./prec)
        
        dist = st.norm(mean - mean_, std + std_)
        l1 = dist.logsf(0)
        l2 = np.log(1-np.exp(l1))
        return l1 - l2
