**Aproach** 
I used claude to help me go clause by clause on each program and help me write up some clean tests that would be testing the normal functionality of what the spec said it should do. Then I thought of the edge cases and had claude write it up for me. I didn't want it to write some of the edge cases so I could internalize what functions or methods could be buggy and affect accuracy of the result. 



**interval_merger**
- C1: reversed tuple raises `ValueError`, reversed tuple in a mixed list raises `ValueError` and did not rearrange 
- C2: output sorted ascending when input is out of order
- C3: overlapping intervals merge, touching endpoints merge, adjacent stays separate, multiple intervals span full range, partial merge in mixed list, duplicate intervals collapse
- C4: zero-length interval merges with larger, zero-length interval alone stays as-is
- C5: empty input returns empty list
- C6: input list not mutated after call


**lru_cache**
- C1: zero capacity raises `ValueError`, negative capacity raises `ValueError`
- C2: basic put and get, TTL=None never expires
- C3: re-put replaces value, re-put clears old TTL
- C4: evicts least recently used when full, len stays at capacity after eviction, new entry present after eviction
- C5: get refreshes LRU position, put on existing key refreshes LRU position
- C6: expired entry raises `KeyError`, expired entry removed from len
- C7: len excludes expired entries without accessing them, len of empty cache is 0

**cart**
- C1: zero qty raises `ValueError`, negative qty raises `ValueError`, negative price raises `ValueError`, duplicate SKU raises `ValueError`
- C2: valid code returns `True`, unknown code returns `False`, duplicate code returns `False`, case-sensitive code returns `False`
- C3: SAVE10, SAVE20, FLAT5, BOGO_BAGEL, FREESHIP all work correctly
- C4: SAVE10 and SAVE20 mutually exclusive both directions, FLAT5 stacks with SAVE10, FLAT5 stacks with SAVE20
- C5: BOGO applies before percent discount, FLAT5 applies after percent discount, FLAT5 clamps at zero, FREESHIP exact boundary, FREESHIP below boundary, FREESHIP not waived when discounts drop below boundary. 
- C6: banker's rounding on percent discount
- C7: empty cart returns zero, empty cart with codes returns zero


**Edge Casses for Interval Merger**
I made sure that the single intervals were not being altered behind the senes and tested that it returned as it was inputed. When there was duplicate intervals, tested to make sure that they returned as one interval. I also made sure that when there were a mix of mergable and unmergable intervals that the correct intervals merged and the others were left as is. 
Also wanted to make sure that it ordered negative numbers appropriately, and the tests made sure that the merging was ordered correctly and the misordering of single interval threw an error. As well as the larger numbers, tested to make sure that two intervals where merged correctly. 

**Edge Cases for LRU Cache** 
The cases that I invented for the LRU cache program was one that tested that the ordering was based on the LRU and not the TTL. I also wanted to make sure that when the parts of the key are changed the entire key is replaced (done by changing the ttl and the value of the key) and so I tested that the key ouputed a new value and has the same len as before. Also checked that the len decreases when the values expire.

**Edge Cases for Cart**
For cart module, I wanted to make sure that the BOGO_BAGEL was not rounding up the integer division and gave a discount of only one bagel when there was three. Also that BOGO discount only applied to the bagels and not other items like apples. Made sure that the FLat5 was applied even without a percent discount. I tested Flat5 was applied after the BOGO and percentage discounts. I also tested when no code was applied to make sure that none of the codes were automatically running specifically the Freehship code. 
I also wanted to make sure that Flat5 and Freeship codes were applying independently so I tested where the Flat5 is applied but the Freeship code is not applicable so it should amount to just the discount of Flat5. I wanted to make sure that Freeship was also not adding the shipping to its calculation so I created a senario where it is below the amount before shipping costs and it should return the cost without the Freeship code applied. 



**What was Difficult in Testing** 
Personally I found that writing tests for things that shouldn't happen was a lot harder than things that should happen. When I was dealing with the cart program I had to think of senarios where the pre-shipping cost is less than the amount needed for the free shipping code, because Claude tends to think more on the side of what should happen but not on what shouldn't happen, I had to come up with the senario that would make sure the computation is dependent on the pre-shipping cost and not total. So in this way I have to think of senarios that would isolate the behavior that I want and be able to display it in a way that I *know* it was successful. 

