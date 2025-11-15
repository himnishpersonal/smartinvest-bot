# 🤖 SmartInvest Discord Bot

A personal stock recommendation and portfolio management Discord bot powered by machine learning.

## 🚀 Features

- **Real-time Stock Analysis**: Get instant analysis of any stock ticker
- **Portfolio Management**: Track and optimize your personal portfolio
- **News Integration**: Stay updated with relevant financial news
- **ML-Powered Recommendations**: AI-driven investment suggestions
- **Risk Assessment**: Understand the risk profile of your investments
- **Price Alerts**: Get notified when stocks hit your target prices

## 📋 Requirements

- Python 3.8+
- Discord Bot Token
- NewsAPI Key (optional)
- PostgreSQL Database (optional)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd smartinvest-bot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install TA-Lib (Technical Analysis Library)
TA-Lib requires C dependencies. Install based on your OS:

**macOS:**
```bash
brew install ta-lib
pip install TA-Lib
```

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib
```

**Windows:**
Download the appropriate wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)

### 5. Environment Setup
```bash
cp .env.example .env
# Edit .env with your actual values
```

## 🔑 Getting API Keys

### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Click "Add Bot"
5. Copy the token and paste it in your `.env` file

### NewsAPI Key (Optional)
1. Go to [NewsAPI](https://newsapi.org/)
2. Sign up for a free account
3. Copy your API key and paste it in your `.env` file

### Discord Channel ID
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on your desired channel
3. Click "Copy ID"
4. Paste it in your `.env` file

## 🚀 Running the Bot

```bash
python main.py
```

## 📁 Project Structure

```
smartinvest-bot/
├── data/           # Data processing and storage
├── features/       # Feature engineering
├── models/         # ML models and algorithms
├── utils/          # Helper functions
├── tests/          # Unit and integration tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. It is not financial advice. Always do your own research before making investment decisions.
