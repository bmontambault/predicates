import pandas as pd
import numpy as np
from .utils import get_filters_masks, get_filters_mask

class Pivot(object):
    
    def __init__(self, data=None, dtypes=None, attribute=None, value=None, context=None, mask=None, context_mask=None):
        self.attribute = attribute
        if data is not None:
            self.set_data(data, dtypes, mask, context_mask)
            
    def set_data(self, data, dtypes, mask=None, context_mask=None):
        self.context_mask = get_filters_masks(data, dtypes, self.context) if context_mask is None else context_mask
        self.mask = get_filters_mask(data, dtypes, {self.attribute: self.value}) if mask is None else mask
        self.mask = self.mask.loc[self.context_mask].reset_index(drop=True)
        self.dtypes = dtypes
        self.data = data.loc[self.context_mask].reset_index(drop=True).assign(predicate=self.mask)
        self.dtype = self.dtypes[self.attribute]
        
    def get_plot_data(self, y='count', max_bins=25):
        if self.dtype == 'nominal':
            grouper = self.attribute
        else:
            num_bins = self.get_num_bins(max_bins)
            grouper = pd.cut(self.data[self.attribute], bins=num_bins)
        
        if type(y) == str:
            if y == 'count':
                agg_col = self.data.columns[0] if self.data.columns[0] != self.attribute else self.data.columns[1]
                agg_func = 'count' 
                columns = [self.attribute, 'count', 'predicate']
            else:
                agg_col = y
                agg_func = 'mean'
                columns = [self.attribute, y, 'predicate']
            d = self.data.groupby(grouper)[[agg_col, 'predicate']].agg({agg_col: agg_func, 'predicate': 'mean'}).reset_index()
            d.columns = columns
        else:
            d = y.groupby(grouper).mean().reset_index()
            d['predicate'] = d[self.attribute].map(self.data.predicate.groupby(grouper).mean())
            d.columns = [self.attribute, 'score', 'predicate']
        
        if self.dtype != 'nominal':
            d[self.attribute] = d[self.attribute].apply(lambda x: np.round((x.left+x.right)/2,2))
        return d
    
    def get_num_bins(self, max_bins):
        best_score = np.inf
        best_num_bins = None
        for num_bins in range(2, max_bins+1):
            d = self.data.groupby(pd.cut(self.data[self.attribute], bins=num_bins)).predicate.mean()
            score = (d*(1-d)).sum()
            if score<best_score:
                best_score = score
                best_num_bins = num_bins
            if score == 0:
                return best_num_bins
        return best_num_bins
