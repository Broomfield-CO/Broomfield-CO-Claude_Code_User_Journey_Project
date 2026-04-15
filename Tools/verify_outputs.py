import os
import pandas as pd

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
raw = os.path.join(base, 'raw_user_journeys.csv')
allf = os.path.join(base, 'base_user_journeys.csv')
lastf = os.path.join(base, 'base_user_journeys_full_visit_path.csv')

def count_rows(path):
    # count rows efficiently
    cnt = 0
    for _ in pd.read_csv(path, chunksize=100000):
        cnt += _.shape[0]
    return cnt

def unique_visits_in_raw(path):
    s = set()
    for chunk in pd.read_csv(path, usecols=['fullVisitorId','visitNumber'], chunksize=200000, dtype={'fullVisitorId':str,'visitNumber':int}):
        for fid, vn in zip(chunk['fullVisitorId'], chunk['visitNumber']):
            s.add((fid, int(vn)))
    return len(s)

if __name__ == '__main__':
    print('Counting rows in all-hits output...')
    all_rows = count_rows(allf)
    print('all_rows', all_rows)
    print('Counting rows in last-hit output...')
    last_rows = count_rows(lastf)
    print('last_rows', last_rows)
    print('Counting unique visits in raw file... (may take a while)')
    uniq = unique_visits_in_raw(raw)
    print('unique_visits_in_raw', uniq)
