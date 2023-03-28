import pandas as pd
from .Predicate import Predicate

def unique(l):
    a = []
    for li in l:
        if li not in a:
            a.append(li)
    return a

def get_index(l, index):
    return [l[i] for i in index]

def row_to_predicates(row, data, dtypes):
    attributes = list(data.columns)
    predicates = []
    for k,v in row.items():
        dtype = dtypes[k]
        if dtype in ('numeric', 'date'):
            values = [v.left, v.right]
        elif dtype == 'ordinal':
            values = [v, v]
        else:
            values = [v]
        predicates.append(Predicate(attributes=attributes, **{k: values}))
    return predicates

def data_to_predicates(data, d, dtypes):
    return [a for b in [row_to_predicates(row, d, dtypes) for index,row in data.iterrows()] for a in b]

def data_to_predicates(data, original_data, dtypes):
    attr_predicates = {}
    attr_indices = {}
    attributes = list(data.columns)
    for attr in attributes:
        dtype = dtypes[attr]
        predicates = []
        indices = {}
        for index,v in data[attr].sort_values().items():
            if dtype in ('numeric', 'date'):
                values = [v.left, v.right]
            elif dtype == 'ordinal':
                values = [v, v]
            else:
                values = [v]
            
            predicate = Predicate(attributes=attributes, **{attr: values}, adj_outer={attr: {'left': predicates[-1]}} if len(predicates)>0 and dtype != 'nominal' else {attr: {}})
            if predicate in predicates:
                predicate_index = predicates.index(predicate)
            else:
                if len(predicates)>0 and dtype != 'nominal':
                    predicates[-1].adj_outer[attr]['right'] = predicate
                predicate.set_data(original_data, dtypes)
                predicates.append(predicate)
                predicate_index = len(predicates)-1
                
            indices[index] = predicate_index
        attr_predicates[attr] = predicates
        attr_indices[attr] = indices
        
    indices_df = pd.DataFrame({k: list(list(zip(*sorted([(ki,vi) for ki,vi in v.items()], key=lambda x: x[0])))[1]) for k,v in attr_indices.items()})
    return attr_predicates, indices_df