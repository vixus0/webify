from __future__ import print_function
from webify import Search

def test_searches(query):
    for cls in Search.__subclasses__():

        test_search = {
            "page":1, 
            "max_res":5,
            "start_res":1,
            "terms":query
            }
        
        s = cls()

        print(s)
        s.search(test_search)
        print(s.results)
        print("\n\n")

        print(s.results[0].resolve_url())
        print("\n\n\n")

