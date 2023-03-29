import pandas as pd
import numpy as np
from .utils import get_filter_mask
from .utils import get_filters_masks
from .utils import get_filters_text

class Pivot(object):
    
    def __init__(self, data=None, dtypes=None, attribute=None, value=None, context=None, mask=None, context_mask=None):
        self.attribute = attribute
        self.value = value
        self.context = context
        if data is not None:
            self.set_data(data, dtypes, mask, context_mask)
            
    def set_data(self, data, dtypes, mask=None, context_mask=None):
        self.context_mask = get_filters_masks(data, dtypes, self.context) if context_mask is None else context_mask
        self.mask = get_filter_mask(data, dtypes, {self.attribute: self.value}) if mask is None else mask
        self.mask = self.mask.loc[self.context_mask].reset_index(drop=True)
        self.dtypes = dtypes
        self.data = data.loc[self.context_mask].reset_index(drop=True).assign(predicate=self.mask)
        self.dtype = self.dtypes[self.attribute]
        
    def get_plot_data_text(self, y='count', min_bins=2, max_bins=25, to_dict=False):
        if self.dtype == 'nominal':
            grouper = self.data[self.attribute]
        elif self.dtype == 'date':
            grouper = pd.Grouper(freq='MS', key=self.attribute)
        else:
            # num_bins = self.get_num_bins(min_bins, max_bins)
            grouper = pd.cut(self.data[self.attribute], bins=max_bins)
        
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
            y_agg = self.data[agg_col].groupby(self.mask).agg(agg_func)
        else:
            d = y.to_frame()
            d.columns = ['y']
            if self.dtype == 'date':
                d[self.attribute] = self.data[self.attribute]

            d = d.groupby(grouper).y.mean().reset_index()
            print(d)

            d['predicate'] = d[self.attribute].map(self.data.groupby(grouper).predicate.mean())

            print(d)
            d.columns = [self.attribute, 'score', 'predicate']
            y_agg = y.groupby(self.mask).mean()
        
        y_agg_in = y_agg[True]
        y_agg_out = y_agg[False]
        gt = y_agg_in > y_agg_out
        if self.dtype not in ('nominal', 'date'):
            d[self.attribute] = d[self.attribute].apply(lambda x: x.left)
        
        context_text = get_filters_text(self.context, self.dtypes)
        comparison_text = get_filters_text({self.attribute: self.value}, self.dtypes)
        value_text = f'{"value" if type(y) != str else y if y == "count" else agg_func + " " + y} is {"greater" if gt else "less"} ({np.round(y_agg_in,2)}/{np.round(y_agg_out,2)})'
        if to_dict:
            d = d.dropna().to_dict('records')
        return d, (context_text, comparison_text, value_text)
    
    def get_num_bins(self, min_bins, max_bins):
        best_score = np.inf
        best_num_bins = None
        for num_bins in range(min_bins, max_bins+1):
            d = self.data.groupby(pd.cut(self.data[self.attribute], bins=num_bins)).predicate.mean()
            score = (d*(1-d)).sum()
            if score<best_score:
                best_score = score
                best_num_bins = num_bins
            if score == 0:
                return best_num_bins
        return best_num_bins
