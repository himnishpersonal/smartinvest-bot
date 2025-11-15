# Project Cleanup Plan

## 🎯 Goal: Clean, Organized, Production-Ready Structure

---

## ✅ KEEP (Essential Files)

### Core Application
- `bot_with_real_data.py` ✅ Main Discord bot
- `config.py` ✅ Configuration
- `requirements.txt` ✅ Dependencies
- `.env` ✅ API keys (not shown but exists)
- `smartinvest_dev.db` ✅ Database

### Code Modules
- `data/` ✅ All files (collectors, storage, schema)
- `features/` ✅ All files (technical, fundamental, sentiment)
- `models/` ✅ All files (training, feature_pipeline, scoring)
- `utils/` ✅ All files (helpers, validators)

### Scripts (Essential)
- `scripts/load_full_sp500.py` ✅ NEW - Load all 500 stocks
- `scripts/daily_refresh.py` ✅ Daily data refresh
- `scripts/setup_cron.py` ✅ Automation setup
- `scripts/train_model_v2.py` ✅ ML training (v2 - working)
- `scripts/fetch_news_sentiment.py` ✅ News collection

### Documentation (Keep Best)
- `README.md` ✅ Main project overview
- `TECHNICAL_DOCUMENTATION.md` ✅ Complete technical guide
- `AUTOMATION_GUIDE.md` ✅ Automation setup
- `EXPANSION_PLAN.md` ✅ Future roadmap
- `PHASE_1_2_COMPLETE.md` ✅ Implementation status
- `QUICK_START_AUTOMATION.md` ✅ Quick reference
- `TRADING_BOT_INTEGRATION.md` ✅ Trading bot guide

---

## 🗑️ DELETE (Obsolete/Redundant)

### Old Test Files
- `test_alphavantage.py` ❌ Alpha Vantage no longer used
- `verify_setup.py` ❌ Obsolete verification
- `run_tests.py` ❌ Old test runner
- `demo_pipeline.py` ❌ Demo file

### Obsolete Scripts
- `scripts/load_sp500.py` ❌ Wikipedia blocked, use load_full_sp500.py
- `scripts/train_model.py` ❌ Old version, use train_model_v2.py
- `scripts/load_full_data.py` ❌ Redundant with load_full_sp500.py
- `scripts/test_pipeline.py` ❌ Obsolete test

### Old Loaders (Root Level)
- `load_incremental.py` ❌ Superseded by scripts/
- `load_real_stocks.py` ❌ Superseded by scripts/
- `load_sp100.py` ❌ Use load_full_sp500.py instead
- `load_test_data.py` ❌ Test data, not needed

### Redundant Documentation
- `ANSWER_REAL_DATA.md` ❌ Obsolete
- `REAL_TIME_DATA_SOLUTION.md` ❌ Covered in TECHNICAL_DOCUMENTATION
- `LOAD_DATA_NOW.md` ❌ Covered in QUICK_START_AUTOMATION
- `SETUP_CHECKLIST.md` ❌ Covered in README
- `START_BOT.md` ❌ Covered in README
- `START_HERE.md` ❌ Covered in README
- `docs/` ❌ Entire folder (old/redundant docs)

---

## 📁 ARCHIVE (Keep for Reference)

### Tests (Move to archive/)
- `tests/` → `archive/tests/` ✅ Keep for future testing

### Old Models (Move to archive/)
- `models/saved_models/test_model*.pkl` → Archive old test models

---

## 🎯 FINAL CLEAN STRUCTURE

```
smartinvest-bot/
├── README.md                          ⭐ Start here
├── config.py                          ⚙️ Configuration
├── requirements.txt                   📦 Dependencies
├── bot_with_real_data.py             🤖 Main bot
├── smartinvest_dev.db                💾 Database
│
├── data/                              📊 Data layer
│   ├── collectors.py
│   ├── storage.py
│   └── schema.py
│
├── features/                          🔧 Feature engineering
│   ├── technical.py
│   ├── fundamental.py
│   └── sentiment.py
│
├── models/                            🧠 ML models
│   ├── training.py
│   ├── feature_pipeline.py
│   ├── scoring.py
│   └── saved_models/
│       └── model_latest.pkl
│
├── utils/                             🛠️ Utilities
│   ├── helpers.py
│   └── validators.py
│
├── scripts/                           📜 Operational scripts
│   ├── load_full_sp500.py           🔄 Load 500 stocks
│   ├── daily_refresh.py             🔄 Daily update
│   ├── setup_cron.py                ⏰ Automation
│   ├── train_model_v2.py            🧠 Train ML
│   └── fetch_news_sentiment.py      📰 News
│
├── docs/                              📚 Documentation
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── AUTOMATION_GUIDE.md
│   ├── EXPANSION_PLAN.md
│   ├── PHASE_1_2_COMPLETE.md
│   ├── QUICK_START_AUTOMATION.md
│   └── TRADING_BOT_INTEGRATION.md
│
├── logs/                              📝 Logs (created by cron)
│   └── daily_refresh.log
│
└── archive/                           📦 Old files (reference)
    ├── tests/
    └── old_scripts/
```

---

## 📊 CLEANUP STATS

Before Cleanup:
- Total files: ~60+ at root level
- Documentation: 18 files scattered
- Scripts: 12 files (8 obsolete)
- Test files: 6+ scattered

After Cleanup:
- Root files: 5 essential
- Documentation: 6 organized in docs/
- Scripts: 5 essential in scripts/
- Everything organized by purpose

**Space saved:** ~20-30 MB (removing redundant docs/scripts)
**Organization:** ⭐⭐⭐⭐⭐ Clean & professional

---

## ⚠️ SAFETY

All deletions are SAFE because:
1. Obsolete files (already replaced)
2. Redundant documentation (consolidated)
3. Test/demo files (not used in production)
4. Important files moved to archive/ (not deleted)

Database and venv are NEVER touched!

---

Ready to execute? See CLEANUP_EXECUTION.md

