# Tavily Credit Usage Guide

## 📊 Current Usage Per Run

With your current settings (`max_enrichment_jobs: 30`):

```
Jobs to enrich: 30
Unique companies: ~21 (30% are duplicates)
API calls per company: 2 (company info + tech stack)
Total API calls per run: 42
Credits used per run: 42
```

---

## 💰 Monthly Budget Analysis

**Free Tier**: 1000 credits/month

### Your Current Schedule (2 runs/week = 8/month)

| Metric | Value |
|--------|-------|
| Credits per run | 42 |
| Runs per month | 8 |
| **Total credits/month** | **336** |
| Remaining budget | 664 |
| Status | ✅ **Well under budget!** |

**You're using only 34% of your free credits** - very efficient!

---

## 🎯 Usage Scenarios

| Schedule | Runs/Month | Credits/Month | Status |
|----------|------------|---------------|--------|
| **Current (2x/week)** | **8** | **336** | ✅ Optimal |
| Weekly | 4 | 168 | ✅ Very conservative |
| Daily (weekdays) | 20 | 840 | ✅ Still under budget |
| 3x/week | 12 | 504 | ✅ Good balance |

---

## ⚙️ Optimization Options

### If You Want to Enrich More Jobs

| max_jobs | Credits/Run | @ 8 runs/month | Status |
|----------|-------------|----------------|--------|
| 30 (current) | 42 | 336 | ✅ Recommended |
| 40 | 56 | 448 | ✅ More coverage |
| 50 | 70 | 560 | ✅ Maximum coverage |
| 60 | 84 | 672 | ✅ Still OK |
| 70 | 98 | 784 | ✅ Near limit |
| 80 | 112 | 896 | ⚠️ Close to limit |

### If You Want to Run More Frequently

| Schedule | max_jobs=30 | max_jobs=50 | Recommended |
|----------|-------------|-------------|-------------|
| 2x/week (8/mo) | 336 ✅ | 560 ✅ | Both OK |
| 3x/week (12/mo) | 504 ✅ | 840 ✅ | Both OK |
| Daily M-F (20/mo) | 840 ✅ | 1400 ❌ | Use max_jobs=30 |

---

## 💡 Recommendations

### Current Settings (Perfect!)
```yaml
tavily:
  max_enrichment_jobs: 30  # ✅ Keep this
```

**Why it's optimal:**
- Enriches top 30 most relevant jobs
- Only uses 336/1000 credits (34%)
- Room to triple usage if needed
- Caching saves ~30% of API calls
- Best ROI: High quality + Low cost

### If You Need More

**More Jobs**: Increase to `max_enrichment_jobs: 50`
- Uses 560 credits/month @ 8 runs
- Still 44% under budget
- Better for broad job search

**More Runs**: Keep at 30 jobs, run 3x/week
- Uses 504 credits/month @ 12 runs
- Still 50% under budget
- Better for fast-moving markets

### Maximum Settings (Stay Under 1000)

```yaml
# Daily runs on weekdays
max_enrichment_jobs: 30  # = 840 credits/month

# OR

# 2x weekly with max enrichment
max_enrichment_jobs: 70  # = 784 credits/month
```

---

## 📈 How Credits Are Used

### Per Company Enrichment
1. **Company info search** (1 credit)
   - Employee count
   - Funding stage
   - AI-native status
   - Recent news

2. **Tech stack search** (1 credit)
   - Engineering blog posts
   - GitHub repos
   - Stack mentions

**Total: 2 credits per unique company**

### Cache Optimization
- First search: 2 credits
- Duplicate company: 0 credits (cached!)
- Estimated savings: 30% of jobs are duplicates

Example with 30 jobs:
- Without cache: 60 credits
- With cache: 42 credits
- **Savings: 18 credits (30%)**

---

## 🚀 Real-World Example

If you run the pipeline:

```bash
python -m src.main
```

You'll see:
```
[STEP 4.5] Enriching companies via web search (30 jobs)...
  Rate limiting: 1.5s between API calls (be nice to Tavily)
  Progress: 5/30 companies processed
  Progress: 10/30 companies processed
  ...
  ✓ Successfully enriched 21/30 companies
  📊 API calls used: 42 (cache saved 9 calls)
  💰 Credits used: ~42 (1000/month free tier)
```

---

## 🎯 Quick Reference

| Your Question | Answer |
|--------------|--------|
| Credits per run? | **42 credits** |
| Monthly usage? | **336 credits** (8 runs) |
| Budget status? | **✅ 66% remaining** |
| Can increase? | **Yes, 3x more possible** |
| Optimal setting? | **Keep at 30 jobs ✅** |

---

## 📝 To Check Usage Anytime

```bash
# See detailed analysis
python calculate_credits.py

# Run pipeline (shows credits in output)
python -m src.main
```

---

**Bottom Line**: Your current settings are perfect! You're using only 1/3 of your free credits while enriching the top 30 most relevant jobs. No changes needed unless you want to increase coverage.
