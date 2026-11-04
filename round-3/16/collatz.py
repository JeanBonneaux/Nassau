# Longest Collatz chain under 100000
best=(0,0)
cache={1:1}
for n in range(1,100000):
    m=n;path=[]
    while m not in cache:
        path.append(m);m=m//2 if m%2==0 else 3*m+1
    l=cache[m]
    for p in reversed(path):
        l+=1;cache[p]=l
    if cache[n]>best[1]:best=(n,cache[n])
print(best)
