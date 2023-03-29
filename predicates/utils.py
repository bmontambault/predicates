import pandas as pd
import numpy as np
import datetime

def infer_dtype(d, dtype=None):
    if dtype is not None:
        return dtype
    else:
        if d.nunique() == 2:
            return 'binary'
        elif d.apply(lambda x: isinstance(x, datetime.datetime)).all():
            return 'date'
        elif d.apply(lambda x: isinstance(x, float)).all():
            return 'numeric'
        elif d.apply(lambda x: isinstance(x, int)).all():
            return 'ordinal'
        else:
            r = '(20\d{2})-(\d{2})-(\d{2})'
            if d.astype(str).str.match(r).all():
                return 'date'
            else:
                return 'nominal'

def infer_dtypes(df, **kwargs):
    dtypes = {col: infer_dtype(df[col], kwargs.get(col)) for col in df.columns}
    d = list(set(dtypes.values()))
    for di in d:
        dtypes[di] = [k for k,v in dtypes.items() if v == di]
        if di == 'nominal':
            df[dtypes[di]] = df[dtypes[di]].astype(str)
        elif di == 'ordinal':
            df[dtypes[di]] = df[dtypes[di]].astype(int)
        elif di == 'numeric':
            df[dtypes[di]] = df[dtypes[di]].astype(float)
        elif di == 'date':
            df[dtypes[di]] = pd.to_datetime(df[dtypes[di]])
    return dtypes

def encode(df, dtypes):
    df_cols = []
    df_names = []
    for k in df.columns:
        v = dtypes[k]
        d = df[k]
        if dtypes[k] == 'nominal':
            for val in d.unique():
                df_names.append(k + '_' + val)
                df_cols.append((df[k] == val).astype(int))
        elif dtypes[k] == 'date':
            d = pd.to_datetime(d)
            df_names.append(k)
            df_cols.append((d-d.min()) / (d.max() - d.min()))
        else:
            df_names.append(k)
            df_cols.append(df[k])
    df_ = pd.DataFrame(df_cols).T
    df_.columns = df_names
    return df_

def bin_numeric(df, dtypes, num_bins=25):
    rows = []
    for col in df.columns:
        if dtypes[col] in ('numeric', 'date'):
            rows.append(pd.cut(df[col], bins=num_bins))
        else:
            rows.append(df[col])
    return pd.DataFrame(rows).T

def get_filter_mask(data, dtypes, attribute, value):
    dtype = dtypes[attribute]
    d = data[attribute]
    if dtype in ('nominal', 'binary'):
        return d.isin(value)
    elif dtype == 'date':
        return (d >= pd.to_datetime(value[0])) & (d <= pd.to_datetime(value[1]))
    else:
        return (d >= value[0]) & (d <= value[1])

def get_filters_masks(data, dtypes, filters):
    return pd.DataFrame({attr: get_filter_mask(data, dtypes, attr, value) for attr, value in filters.items()})

def get_cols(col_prefix, num_cols=None, cols=None):
    if cols is not None:
        num_cols = len(cols)
    else:
        cols = [f'{col_prefix}_{i}' for i in range(num_cols)]
    return cols, num_cols

def sample_numeric(num_rows, mean=0, sd=1, num_cols=None, cols=None):
    cols, num_cols = get_cols('numeric', num_cols, cols)
    data = np.random.normal(mean, sd, size=(num_rows,num_cols))
    df = pd.DataFrame(data, columns=cols)
    return df

def sample_ordinal(num_rows, minval=0, maxval=5, num_cols=None, cols=None):
    cols, num_cols = get_cols('ordinal', num_cols, cols)
    data = np.random.randint(minval, maxval+1, size=(num_rows,num_cols))
    df = pd.DataFrame(data, columns=cols)
    return df

def sample_binary(num_rows, p=.5, num_cols=None, cols=None):
    cols, num_cols = get_cols('binary', num_cols, cols)
    data = np.random.binomial(1, p, size=(num_rows,num_cols))
    df = pd.DataFrame(data, columns=cols)
    return df

def sample_nominal(num_rows, num_vals=5, num_cols=None, cols=None):        
    cols, num_cols = get_cols('nominal', num_cols, cols)
    if type(num_vals) == list:
        b = []
        a = int(len(cols)/len(num_vals))
        for i in range(len(num_vals)):
            cols_i = cols[a*i:a*(i+1)]
            b.append(sample_nominal(num_rows, num_vals=num_vals[i], cols=cols_i))
        return pd.concat(b, axis=1)
    else:
        data = np.random.randint(0, num_vals, size=(num_rows,num_cols)).astype(str)
        df = pd.DataFrame(data, columns=cols)
        return df

def sample_date(num_rows, start_date='2022-01-01', end_date='2022-12-31', num_cols=None, cols=None):
    cols, num_cols = get_cols('date', num_cols, cols)
    dates = pd.date_range(start_date, end_date)
    data = np.random.choice(dates, size=(num_rows,num_cols))
    df = pd.DataFrame(data, columns=cols)
    return df

def get_dtype_cols(cols, dtypes, dtype):
    return [col for col in cols if dtypes[col] == dtype]

def sample_data(num_rows, dtypes, dtype_kwargs=None):
    if dtype_kwargs is None:
        dtype_kwargs = {}
    cols = list(dtypes.keys())
    all_dtypes = ['numeric', 'ordinal', 'binary', 'nominal', 'date']
    df_list = []
    for dtype in all_dtypes:
        dtype_cols = get_dtype_cols(cols, dtypes, dtype)
        f = eval(f'sample_{dtype}')
        df = f(num_rows, cols=dtype_cols, **dtype_kwargs.get(dtype,{}))
        df_list.append(df)
    return pd.concat(df_list, axis=1)

def get_filters_text(filters, dtypes):
    filters_list = [f'{k} is {get_filter_clause_text(k,v,dtypes[k])}' for k,v in filters.items()]
    if len(filters_list)>0:
        filters = ', '.join(filters_list[:-1]) + ' and ' + filters_list[-1] if len(filters_list)>1 else filters_list[0]
        return filters
    else:
        return ''

def get_filter_clause_text(attribute, value, dtype):
    if dtype in ('nominal', 'list', 'binary'):
        value_str = ', '.join(value[:-1]) + ' or ' + value[-1] if len(value)>1 else value[0]
    else:
        value_str = f'between {value[0]} and {value[1]}'
    return value_str

def get_filters_predicate_text(filters, dtypes):
    return ' & '.join([get_filter_predicate_clause_text(k,v,dtypes[k]) for k,v in filters.items()]).replace("'", '').replace('"', '')

def get_filter_predicate_clause_text(attribute, value, dtype):
    if dtype in ('nominal', 'list', 'binary'):
        return f'{attribute}:{value}'
    else:
        if type(value[0]) == float:
            value[0] = np.round(value[0],2)
        if type(value[1]) == float:
            value[1] = np.round(value[1],2)
        if value[0] is None:
            return f'{attribute}<={value[1]}'
        if value[1] is None:
            return f'{attribute}>{value[0]}'
        else:
            return f'{attribute}:{value}'

def merge_filter_value(value1, value2, dtype):
    if dtype in ('nominal','binary'):
        return list(set(value1+value2))
    else:
        left_val = min(value1[0], value2[0])
        right_val = max(value1[1], value2[1])
        return [left_val, right_val]

def parse_value_string(value_str, dtype):
    values = value_str[1:-1].split(',')#.replace(' ', '').split(',')
    if dtype == 'ordinal':
        values = [int(values[0]), int(values[1])]
    elif dtype == 'numeric':
        values = [float(values[0]), float(values[1])]
    return values
