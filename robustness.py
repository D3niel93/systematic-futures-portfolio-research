"""Conditional day-block intervals, not a selection-adjusted test of signal alpha."""
import argparse
import math
from pathlib import Path
import numpy as np
import pandas as pd

def day_block_intervals(ledger, iterations=10000, seed=20261014):
    f=ledger.copy()
    f['time']=pd.to_datetime(f.time,utc=True,errors='raise')
    f=f.sort_values('time',kind='stable')
    if f.empty or f.time.isna().any() or not np.isfinite(f.pnl).all():
        raise ValueError('Require valid nonempty net-PnL ledger')
    f['gain']=f.pnl.clip(lower=0)
    f['loss']=(-f.pnl).clip(lower=0)
    f['win']=(f.pnl>0).astype(int)
    days=pd.bdate_range(f.time.min().floor('D'),f.time.max().floor('D'))
    ag=f.set_index('time').resample('B').agg(
        {'pnl':'sum','gain':'sum','loss':'sum','win':'sum','quantity':'size'})
    values=ag.reindex(days,fill_value=0).to_numpy(float)
    rng=np.random.default_rng(seed)
    records=[]
    for length in [5,10,20]:
        draws=[]
        for _ in range(iterations):
            starts=rng.integers(0,len(values),size=math.ceil(len(values)/length))
            ix=((starts[:,None]+np.arange(length))%len(values)).ravel()[:len(values)]
            sample=values[ix]
            pnl,gains,losses,wins,n=sample.sum(axis=0)
            equity=np.r_[0.,sample[:,0].cumsum()]
            draws.append([pnl,pnl/n if n else np.nan,gains/losses if losses else np.nan,
                100*wins/n if n else np.nan,(np.maximum.accumulate(equity)-equity).max()])
        a=np.asarray(draws)
        row=dict(block_days=length,iterations=iterations,net_positive_share=float((a[:,0]>0).mean()))
        for i,key in enumerate(['net','expectancy','pf','wr','daily_dd']):
            row[key+'_low'],row[key+'_median'],row[key+'_high']=map(float,np.nanquantile(a[:,i],[.025,.5,.975]))
        records.append(row)
    return pd.DataFrame(records)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations',type=int,default=10000)
    args=parser.parse_args()
    if args.iterations<1: parser.error('iterations must be positive')
    root=Path(__file__).resolve().parent
    result=day_block_intervals(pd.read_csv(root/'data/trades.csv'),args.iterations)
    out=root/'generated';out.mkdir(exist_ok=True)
    result.to_csv(out/'bootstrap_day_blocks.csv',index=False)
    print(result.to_string(index=False))
