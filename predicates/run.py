import os
import dill
import argparse
import json
import time
import pandas as pd
import numpy as np

from rpy2.robjects import Formula
from rpy2.robjects.packages import importr
from rpy2.robjects import numpy2ri, pandas2ri
import rpy2.rinterface_lib.callbacks
import rpy2.robjects as robjects
numpy2ri.activate()
pandas2ri.activate()
RBayesFactor=importr('BayesFactor', suppress_messages=True)

from PredicatesRead import PredicatesRead

def run(path, has_predicates=False, has_frontier=False, has_accepted=False, max_accepted=None, max_steps=None, max_clauses=None, breadth_first=None):
    with open(os.path.join(path, 'predicate_induction.pkl'), 'rb') as f:
        predicate_induction = dill.load(f)
    if has_predicates:
        predicates_path = os.path.join(path, 'predicates')
        predicates = PredicatesRead(predicate_induction.data, predicate_induction.dtypes, predicates_path, predicate_induction.predicate_data)
        predicates.update()
    else:
        predicates = None
    predicate_induction.background = False
    print(predicate_induction)
    predicate_induction.search(predicates.predicates, max_accepted, max_steps, max_clauses, breadth_first)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("has_predicates", type=bool)
    parser.add_argument("has_frontier", type=bool)
    parser.add_argument("has_accepted", type=bool)
    parser.add_argument("path", type=str)
    parser.add_argument("max_accepted")
    parser.add_argument("max_steps")
    parser.add_argument("max_clauses")
    parser.add_argument("breadth_first", type=bool)
        
    args = vars(parser.parse_args())
    args['max_accepted'] = None if args['max_accepted'] == 'None' else int(args['max_accepted'])
    args['max_steps'] = None if args['max_steps'] == 'None' else int(args['max_steps'])
    args['max_clauses'] = None if args['max_clauses'] == 'None' else int(args['max_clauses'])
    run(**args)