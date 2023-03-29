import pandas as pd
from .Pivot import Pivot
from .utils import get_filter_mask
from .utils import get_filters_masks
from .utils import merge_filter_value

class Predicate(object):
    
    def __init__(self, data=None, dtypes=None, attributes=None, attribute_values=None, attribute_mask=None, mask=None, adj_outer=None, adj_inner=None, parents=None, **kwargs):
        self.attributes = list({} if dtypes is None else dtypes.keys()) if attributes is None else attributes
        if attribute_values is None:
            self.attribute_values = {}
            for k,v in kwargs.items():
                if k in self.attributes:
                    self.attribute_values[k] = v
        else:
            self.attribute_values = attribute_values
        self.predicate_attributes = list(self.attribute_values.keys())
        if adj_outer is None:
            self.adj_outer = {}
        else:
            self.adj_outer = adj_outer
        if adj_inner is None:
            self.adj_inner = {}
        else:
            self.adj_inner = adj_inner
        if data is not None:
            self.set_data(data, dtypes, attribute_mask, mask)
        self.parents = parents
        self.is_negated = False
        
    def get_distribution(self, d, mask=None, num_bins=25, include_compliment=False):
        mask = self.mask if mask is None else mask
        if self.is_negated:
            mask = ~mask            
    
        d_ = d[mask]
        if num_bins>len(d_):
            counts = d_.value_counts()
        else:
            counts = pd.cut(d_, bins=num_bins).value_counts()
            counts.index = counts.index.map(lambda x: x.left)
        dist = (counts/counts.sum()).reset_index()
        dist.columns = ['score', 'density']
        
        if include_compliment:
            # dist = pd.concat([dist.assign(predicate=True), self.get_distribution(d, ~mask, 100, False).assign(predicate=False)])
            dist = pd.concat([dist.assign(predicate=True), self.get_distribution(d, ~mask, num_bins, False).assign(predicate=False)])
        return dist
        
    def to_dict(self):
        return {
            'attribute_values': self.attribute_values,
            'negated': self.is_negated
        }
    
    def to_dict_dist(self, d, num_bins=25, include_compliment=False):
        dct = self.to_dict()
        dct['dist'] = self.get_distribution(d, num_bins=num_bins, include_compliment=include_compliment).to_dict('records')
        return dct
            
    
    def is_contained_values(self, values_a, attribute):
        values_b = self.attribute_values[attribute]
        if self.dtypes[attribute] == 'nominal':
            return values_a[0] == values_b[0]
        else:
            return (values_a[0]<=values_b[0]) & (values_a[1]>=values_b[1])
    
    def is_contained_attribute(self, predicate, attribute):
        values_a = predicate.attribute_values[attribute]
        return self.is_contained_values(values_a, attribute)

    def is_contained(self, predicate):
#         other_attr = [attr for attr in predicate.predicate_attributes if attr not in self.predicate_attributes]
#         if len(other_attr) == 0:
#             if len(predicate.mask) == len(self.mask):
#                 return True
            
        for attribute in self.attribute_values:
            if attribute not in predicate.attribute_values:
                return False
#                 vals = self.data.loc[predicate.mask, attribute]
#                 values = list(vals.unique()) if self.dtypes[attribute] == 'nominal' else [vals.min(), vals.max()]
#                 is_contained = self.is_contained_values(values, attribute)
            else:
                is_contained = self.is_contained_attribute(predicate, attribute)
                if not is_contained:
                    return False
        return True
    
    def is_contained_any(self, predicates):
        return any([self.is_contained(predicate) for predicate in predicates])
            
    def set_data(self, data, dtypes, attribute_mask=None, mask=None):
        self.data = data
        self.dtypes = dtypes        
        if attribute_mask is None:
            self.attribute_mask = get_filters_masks(data, dtypes, self.attribute_values)
        else:
            self.attribute_mask = attribute_mask
        if mask is None:
            self.mask = self.attribute_mask.all(axis=1)
        else:
            self.mask = mask
            
    def set_attribute_values(self, attribute_values, attribute_mask=None, mask=None):
        if attribute_mask is None:
            attribute_mask = get_filters_masks(self.data, self.dtypes, self.attribute_values)
        if mask is None:
            mask = attribute_mask.all(axis=1)
        return Predicate(self.data, self.dtypes, attribute_values, attribute_mask, mask)
        
    def set_attribute_value(self, attribute, values, attribute_mask=None, mask=None):
        attribute_values = {k: v for k,v in self.attribute_values.items()}
        attribute_values[attribute] = values
        if attribute_mask is None:
            attribute_mask = self.attribute_mask
        else:
            attribute_mask = self.attribute_mask.copy()
            attribute_mask[attribute] = get_filter_mask(self.data, self.dtypes, attribute, values)
        if mask is None:
            mask = self.mask
        return Predicate(self.data, self.dtypes, attribute_values, attribute_mask, mask)
    
    def get_attribute(self, attribute):
        attribute_values = {attribute: self.attribute_values[attribute]}
        adj_outer = {attribute: self.adj_outer.get(attribute,{})}
        adj_inner = {attribute: self.adj_inner.get(attribute,{})}
        attribute_mask = self.attribute_mask[[attribute]]
        mask = attribute_mask[attribute]
        return Predicate(self.data, self.dtypes, None, attribute_values, attribute_mask, mask, adj_outer, adj_inner)
    
    def merge_adjacent_attribute(self, predicate, attribute, side):
        adj_outer = {}
        if side == 'right':
            if 'right' in predicate.adj_outer[attribute]:
                adj_outer['right'] = predicate.adj_outer[attribute]['right']
            if 'left' in self.adj_outer[attribute]:
                adj_outer['left'] = self.adj_outer[attribute]['left']
            adj_inner = {'right': self.get_attribute(attribute)}
            if attribute in self.adj_inner and 'left' in self.adj_inner[attribute]: 
                adj_inner['left'] = self.adj_inner[attribute]['left']
        elif side == 'left':        
            if 'right' in self.adj_outer[attribute]:
                adj_outer['right'] = self.adj_outer[attribute]['right']
            if 'left' in predicate.adj_outer[attribute]:
                adj_outer['left'] = predicate.adj_outer[attribute]['left']
            adj_inner = {'left': self.get_attribute(attribute)}
            if attribute in self.adj_inner and 'right' in self.adj_inner[attribute]: 
                adj_inner['right'] = self.adj_inner[attribute]['right']
        return adj_outer, adj_inner
    
    def add_attribute(self, predicate, attribute):
        attribute_values = {k: v for k,v in self.attribute_values.items()}
        attribute_values[attribute] = predicate.attribute_values[attribute]
        attribute_mask = self.attribute_mask.copy()
        attribute_mask[attribute] = predicate.attribute_mask[attribute]
        mask = self.mask & predicate.mask
        
        adj_outer = {k: v for k,v in self.adj_outer.items()}
        for k,v in predicate.adj_outer.items():
            adj_outer[k] = v
        adj_inner = {k: v for k,v in self.adj_inner.items()}
        for k,v in predicate.adj_inner.items():
            adj_inner[k] = v
        predicate = Predicate(self.data, self.dtypes, self.attributes, attribute_values, attribute_mask, mask, adj_outer, adj_inner, parents=[self, predicate])
        return predicate
    
    def merge_attribute_side(self, predicate, attribute, side):
        dtype = self.dtypes[attribute]
        attribute_values = {k: v for k,v in self.attribute_values.items()}
        attribute_mask = self.attribute_mask.copy()
        if attribute in self.attributes:
            attribute_values[attribute] = merge_filter_value(attribute_values[attribute], predicate.attribute_values[attribute], dtype)
            attribute_mask[attribute] = attribute_mask[attribute] | predicate.attribute_mask[attribute]
        else:
            attribute_values[attribute] = predicate.attribute_values[attribute]
            attribute_mask[attribute] = predicate.attribute_mask[attribute]
        
        adj_outer = {k: v for k,v in predicate.adj_outer.items()}
        adj_inner = {k: v for k,v in predicate.adj_inner.items()}
        adj_outer_attr, adj_inner_attr = self.merge_adjacent_attribute(predicate, attribute, side)
        adj_outer[attribute] = adj_outer_attr
        adj_inner[attribute] = adj_inner_attr
        predicate = Predicate(self.data, self.dtypes, self.attributes, attribute_values, attribute_mask, None, adj_outer, adj_inner, parents=[self, predicate])
        return predicate
    
    def pivot(self, attribute, data=None):
        other_attributes = [attr for attr in self.predicate_attributes if attr != attribute]
        return Pivot(
            data if self.data is None else self.data,
            self.dtypes, attribute, self.attribute_values[attribute],
            {attr:self.attribute_values[attr] for attr in other_attributes},
            self.attribute_mask[attribute],
            self.attribute_mask[other_attributes].all(axis=1),
        )        
    
    def set_attribute_side(self, predicate, attribute, side):
        dtype = self.dtypes[attribute]
        attribute_values = {k: v for k,v in self.attribute_values.items()}
        attribute_mask = self.attribute_mask.copy()
        attribute_values[attribute] = predicate.attribute_values[attribute]
        attribute_mask[attribute] = predicate.attribute_mask[attribute]
        
        adj_outer = {k: v for k,v in predicate.adj_outer.items()}
        adj_inner = {k: v for k,v in predicate.adj_inner.items()}
        adj_outer[attribute] = predicate.adj_outer[attribute]
        adj_inner[attribute] = predicate.adj_inner.get(attribute,{})
        predicate = Predicate(self.data, self.dtypes, self.attributes, attribute_values, attribute_mask, None, adj_outer, adj_inner)
        return predicate
    
    def get_adjacent_attribute_inner(self, attribute):
        return [(self.set_attribute_side(v, attribute, k),v) for k,v in self.adj_inner.get(attribute,{}).items()]

    def get_adjacent_attribute_outer(self, attribute):
        return [(self.merge_attribute_side(v, attribute, k),v) for k,v in self.adj_outer.get(attribute,{}).items()]
    
    def __eq__(self, predicate):
        return self.attribute_values == predicate.attribute_values
        
    def bf(self, target, bf_func, option=None):
        data = self.get_data(option)
        if option in self.attributes:
            a = data.loc[data.predicate, target]
            b = data.loc[~data.predicate, target]
        elif option == '~':
            b = data[target]
            a = self.get_data('~')[target]
        else:
            a = data[target]
            b = self.get_data('~')[target]
        return bf_func(a, b)
    
    def __repr__(self):
        return ' '.join([f'{k}:{v}' for k,v in self.attribute_values.items()])
