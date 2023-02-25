class PredicateInduction(object):
    
    def __init__(self, target, attribute_predicates, score_func):
        self.target = target
        self.attribute_predicates = attribute_predicates
        self.score_func = score_func
        self.predicate_score = {}
        self.predicate_res = {}
        
    def score(self, predicate, **kwargs):
        if predicate.__repr__() not in self.predicate_score:
            score, res = self.score_func(self.target, predicate.mask, None, True, **kwargs)
            self.predicate_score[predicate.__repr__()] = score
            self.predicate_res[predicate.__repr__()] = res
        return self.predicate_score[predicate.__repr__()]

    def merge_predicate_attribute_adjacent(self, predicate, adjacent, attribute):
        children = [p for p,p_ in adjacent if self.score(p)>self.score(p_) and self.score(p)>self.score(predicate)]
        return children
    
    def expand_predicate_attribute(self, predicate, attribute):
        adjacent = predicate.get_adjacent_attribute_outer(attribute)
        children = self.merge_predicate_attribute_adjacent(predicate, adjacent, attribute)
        if len(children)>0:
            return self.expand_predicate_attribute(max(children, key=lambda x: self.score(x)), attribute)
        else:
            return predicate
        
    def fit_predicate_attribute(self, predicate, attribute):
        adjacent = predicate.get_adjacent_attribute_inner(attribute) + predicate.get_adjacent_attribute_outer(attribute)
        children = self.merge_predicate_attribute_adjacent(predicate, adjacent, attribute)
        if len(children)>0:
            return self.fit_predicate_attribute(max(children, key=lambda x: self.score(x)), attribute)
        else:
            return predicate
    
    def fit_other_attributes(self, predicate, attribute):
        for other_attribute in predicate.attribute_values.keys():
            if predicate.dtypes[other_attribute] != 'nominal':
                predicate = self.fit_predicate_attribute(predicate, other_attribute)
        return predicate
        
    def expand_predicate(self, predicate):
        new_predicates = []
        for k,v in self.attribute_predicates.items():
            if k not in predicate.attribute_values.keys():
                for p in v:
                    new_predicate = predicate.add_attribute(p, k)
                    if not new_predicate.is_contained_any(new_predicates):
                        if predicate.dtypes[k] != 'nominal':
                            new_predicate = self.expand_predicate_attribute(new_predicate, k)
                        new_predicate = self.fit_other_attributes(new_predicate, k)
                        if self.score(new_predicate) > self.score(predicate):
                            new_predicates.append(new_predicate)
        return new_predicates
    
    def insert_sorted(self, lst, predicate, breadth_first=False):
        if len(lst) == 0:
            lst.append(predicate)
            return 1
        score = self.score(predicate)
        for i in range(len(lst)):
            i_score = self.score(lst[i])
            if (score > i_score and not breadth_first) or (score > i_score and len(predicate.attribute_values)<=len(lst[i].attribute_values)):
                lst.insert(i, predicate)
                return i
        lst.append(predicate)
        return len(lst)
    
    def insert_sorted_all(self, lst, predicates, breadth_first=False):
        for predicate in predicates:
            self.insert_sorted(lst, predicate, breadth_first)
    
    def search(self, predicates=None, breadth_first=False, num_clauses=None):
        if predicates is None:
            predicates = [a for b in self.attribute_predicates.values() for a in b]
        self.accepted = {i+1: [] for i in range(len(self.attribute_predicates))}
        frontier = sorted(predicates, key=lambda x: self.score(x), reverse=True)
        while len(frontier)>0:
            print(len(frontier))
#             print({k: len(v) for k,v in accepted.items()})
            predicate = frontier.pop(0)
#             print(predicate, self.score(predicate))
            print(predicate, self.score(predicate))
            if not predicate.is_contained_any([a for b in [v for k,v in self.accepted.items() if k>=len(predicate.attribute_values)] for a in b]+frontier):
                if num_clauses is None or len(predicate.attribute_values)<num_clauses:
                    new_predicates = self.expand_predicate(predicate)
                    print([(p, self.score(p)) for p in new_predicates])
                    if len(new_predicates)>0:
                        self.insert_sorted_all(frontier, new_predicates, breadth_first)
                    else:
                        if self.score(predicate)>0:
                            self.insert_sorted(self.accepted[len(predicate.attribute_values)], predicate)
                else:
                    if self.score(predicate)>0:
                        self.insert_sorted(self.accepted[len(predicate.attribute_values)], predicate)
        return self.accepted
