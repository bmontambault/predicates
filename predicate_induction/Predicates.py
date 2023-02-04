from .Predicate import Predicate

class Predicates(object):
    
    def __init__(self, data, dtypes):
        self.data = data
        self.dtypes = dtypes
        
        self.binned_data = self.get_binned_data()
        self.predicates = []
        self.base_predicates = []
        
    def get_base_predicates(self, index, min_val_count=2):
        predicates = {}
        data = self.data.loc[index]
        for col, dtype in self.dtypes.items():
            counts = data[col].value_counts()
            counts_min = counts[counts>=min_val_count]
            for val in counts_min.index:
                if dtype == 'numeric':
                    attribute_value = {col: [val.left, val.right]}
                else:
                    attribute_value = {col: [val]}
            if dtype in predicates:
                predicates[dtype].append(Predicate(attribute_value))
            else:
                predicates[dtype] = [Predicate(attribute_value)]
        return predicates
