from .utils import get_filter_mask
from .utils import get_filters_masks
from .utils import merge_filter_value

class Predicate(object):
    
    def __init__(self, data=None, dtypes=None, attributes=None, attribute_values=None, attribute_mask=None, mask=None, **kwargs):
        self.attributes = list(dtypes.keys()) if attributes is None else attributes
        if attribute_values is None:
            self.attribute_values = {}
            for k,v in kwargs.items():
                if k in self.attributes:
                    self.attribute_values[k] = v
        else:
            self.attribute_values = attribute_values
        self.predicate_attributes = list(self.attribute_values.keys())
        if data is not None:
            self.set_data(data, dtypes)
            
    def set_data(self, data, dtypes):
        self.data = data
        self.dtypes = dtypes
        if self.attribute_values is None:
            self.attribute_mask = get_filters_masks(data, dtypes, self.attribute_values)
        if self.mask is None:
            self.mask = self.attribute_mask.all(axis=1)
            
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
            attribute_mask[attribute] = get_filter_mask(self.data, self.dtypes, attribute, value)
        if mask is None:
            mask = self.mask
        return Predicate(self.data, self.dtypes, attribute_values, attribute_mask, mask)
    
    def merge_attribute(self, predicate, attribute):
        attribute_values = {k: v for k,v in self.attribute_values.items()}
        if attribute in self.attributes:
            attribute_values[attribute] = merge_filter_value(attribute, attribute_values[attribute], predicate.attribute_values[attribute], self.dtypes[attribute])
            
        else:
            attribute_values[attribute] = predicate.attribute_values[attribute]
    
    def merge_attribute_adjacent(self, adjacent, attribute):
        if len(adjacent)>0:
            new_predicate = max([self.merge_attribute(adj) for adj in adjacent], key=lambda x: x.bf)
            if new_predicate.bf > self.bf:
                return new_predicate.expand_attribute(attribute)
            else:
                return self, False
        else:
            return self, False
    
    def expand_attribute(self, attribute):
        adjacent = self.adjacent.get(attribute,[])
        return self.merge_adjacent(adjacent)
        
    def refine_attribute(self, attribute):
        adjacent = self.parents.get(attribute,[])
        return self.merge_adjacent(adjacent)
    
    def __eq__(self, predicate):
        return self.attribute_values == predicate.attribute_values
    
    def get_data(self, option=None):
        if option in self.attributes:
            mask = self.attribute_mask[[attr for attr in self.attributes if attr != option]].all(axis=1)
            return self.data.loc[mask].assign(predicate=self.attribute_mask[option])
        elif option == '~':
            return self.data.loc[~self.mask]
        else:
            return self.data.loc[self.mask]
        
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
