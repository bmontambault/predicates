from .utils import get_filter_mask
from .utils import get_filters_masks

class Predicate(object):
    
    def __init__(self, data, dtypes, attribute_values=None, attribute_mask=None, mask=None, **kwargs):
        self.data = data
        self.dtypes = dtypes
        self.attributes = list(dtypes.keys())
        if attribute_values is None:
            self.attribute_values = {}
            for k,v in kwargs.items():
                if k in self.attributes:
                    self.attribute_values[k] = v
        else:
            self.attribute_values = attribute_values
        self.predicate_attributes = list(self.attribute_values.keys())

        if attribute_values is None:
            self.attribute_mask = get_filters_masks(data, dtypes, self.attribute_values)
        else:
            self.attribute_mask = attribute_mask
        if mask is None:
            self.mask = self.attribute_mask.all(axis=1)
        else:
            self.mask = mask
            
    def set_attribute_values(self, attribute_values, attribute_mask=None, mask=None):
        if attribute_mask is None:
            attribute_mask = get_filters_masks(data, dtypes, self.attribute_values)
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
