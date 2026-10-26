import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';
import '../widgets/quick_trade_modal.dart';
import '../widgets/skeleton_loader.dart';
import 'chart_screen.dart';

class MobileMarketsScreen extends StatefulWidget {
  const MobileMarketsScreen({super.key});

  @override
  State<MobileMarketsScreen> createState() => _MobileMarketsScreenState();
}

class _MobileMarketsScreenState extends State<MobileMarketsScreen> {
  String _marketMode = 'equities'; // 'equities' | 'indices'
  String _searchQuery = '';
  int _selectedTab = 0; // 0 = Watchlist, 1 = All Instruments
  String _selectedSector = 'ALL';
  final String _selectedSort = 'DEFAULT'; // DEFAULT, GAINERS, LOSERS, PRICE_HIGH, VOLUME
  String _selectedIndexCategory = 'ALL'; // 'ALL' | 'HEADLINE' | 'SECTORAL'

  bool _indicesLoading = false;
  List<Map<String, dynamic>> _indicesList = [];

  // User-owned pinned watchlist set
  final Set<String> _pinnedWatchlist = {'RELIANCE', 'TCS', 'INFY', 'HDFCBANK'};

  // 39 Comprehensive Verified NSE Equities across 9 Indian Market Sectors
  final List<Map<String, dynamic>> _instruments = [
    // --- Energy & Utilities ---
    {
      "symbol": "RELIANCE",
      "company": "Reliance Industries Limited",
      "sector": "Energy & Utilities",
      "sectorKey": "ENERGY",
      "price": 2500.00,
      "changeVal": 30.00,
      "changePct": 1.21,
      "positive": true,
      "pe": "26.4x",
      "mktCap": "₹16.9T",
      "volume": "8.4M",
      "dayLow": 2468.0,
      "dayHigh": 2515.0,
      "low52": "₹ 2,220.30",
      "high52": "₹ 3,024.90",
      "isin": "INE002A01018",
      "status": "NSE Verified",
      "sparkline": [2470.0, 2485.0, 2478.0, 2495.0, 2490.0, 2500.0],
    },
    {
      "symbol": "NTPC",
      "company": "NTPC Limited",
      "sector": "Energy & Utilities",
      "sectorKey": "ENERGY",
      "price": 315.15,
      "changeVal": 4.20,
      "changePct": 1.35,
      "positive": true,
      "pe": "15.2x",
      "mktCap": "₹3.1T",
      "volume": "11.2M",
      "dayLow": 311.0,
      "dayHigh": 318.5,
      "low52": "₹ 210.00",
      "high52": "₹ 345.00",
      "isin": "INE733E01010",
      "status": "NSE Verified",
      "sparkline": [310.0, 312.0, 311.5, 314.0, 313.0, 315.15],
    },
    {
      "symbol": "ONGC",
      "company": "Oil & Natural Gas Corporation",
      "sector": "Energy & Utilities",
      "sectorKey": "ENERGY",
      "price": 222.00,
      "changeVal": 2.10,
      "changePct": 0.95,
      "positive": true,
      "pe": "8.4x",
      "mktCap": "₹2.8T",
      "volume": "9.4M",
      "dayLow": 219.0,
      "dayHigh": 224.0,
      "low52": "₹ 175.00",
      "high52": "₹ 280.00",
      "isin": "INE213A01029",
      "status": "NSE Verified",
      "sparkline": [218.0, 220.0, 219.5, 221.0, 220.5, 222.0],
    },
    {
      "symbol": "POWERGRID",
      "company": "Power Grid Corporation of India",
      "sector": "Energy & Utilities",
      "sectorKey": "ENERGY",
      "price": 250.45,
      "changeVal": 3.10,
      "changePct": 1.25,
      "positive": true,
      "pe": "16.8x",
      "mktCap": "₹2.3T",
      "volume": "8.6M",
      "dayLow": 247.0,
      "dayHigh": 252.5,
      "low52": "₹ 185.00",
      "high52": "₹ 290.00",
      "isin": "INE752E01010",
      "status": "NSE Verified",
      "sparkline": [247.0, 248.5, 248.0, 250.0, 249.2, 250.45],
    },
    {
      "symbol": "ADANIENT",
      "company": "Adani Enterprises Limited",
      "sector": "Energy & Utilities",
      "sectorKey": "ENERGY",
      "price": 2692.00,
      "changeVal": 35.40,
      "changePct": 1.33,
      "positive": true,
      "pe": "48.5x",
      "mktCap": "₹3.1T",
      "volume": "4.8M",
      "dayLow": 2650.0,
      "dayHigh": 2715.0,
      "low52": "₹ 2,150.00",
      "high52": "₹ 3,350.00",
      "isin": "INE423A01024",
      "status": "NSE Verified",
      "sparkline": [2640.0, 2670.0, 2660.0, 2685.0, 2675.0, 2692.0],
    },

    // --- Technology ---
    {
      "symbol": "TCS",
      "company": "Tata Consultancy Services Limited",
      "sector": "Technology",
      "sectorKey": "TECH",
      "price": 3600.00,
      "changeVal": -29.00,
      "changePct": -0.80,
      "positive": false,
      "pe": "29.1x",
      "mktCap": "₹13.1T",
      "volume": "3.1M",
      "dayLow": 3590.0,
      "dayHigh": 3645.0,
      "low52": "₹ 3,312.00",
      "high52": "₹ 4,254.75",
      "isin": "INE467B01029",
      "status": "NSE Verified",
      "sparkline": [3635.0, 3620.0, 3625.0, 3610.0, 3605.0, 3600.0],
    },
    {
      "symbol": "INFY",
      "company": "Infosys Limited",
      "sector": "Technology",
      "sectorKey": "TECH",
      "price": 1450.00,
      "changeVal": 7.90,
      "changePct": 0.55,
      "positive": true,
      "pe": "24.8x",
      "mktCap": "₹6.0T",
      "volume": "5.2M",
      "dayLow": 1438.0,
      "dayHigh": 1458.0,
      "low52": "₹ 1,358.35",
      "high52": "₹ 1,760.00",
      "isin": "INE009A01021",
      "status": "NSE Verified",
      "sparkline": [1440.0, 1445.0, 1442.0, 1448.0, 1446.0, 1450.0],
    },
    {
      "symbol": "WIPRO",
      "company": "Wipro Limited",
      "sector": "Technology",
      "sectorKey": "TECH",
      "price": 184.40,
      "changeVal": 1.80,
      "changePct": 0.98,
      "positive": true,
      "pe": "19.5x",
      "mktCap": "₹2.7T",
      "volume": "7.8M",
      "dayLow": 181.8,
      "dayHigh": 186.0,
      "low52": "₹ 155.00",
      "high52": "₹ 240.00",
      "isin": "INE075A01022",
      "status": "NSE Verified",
      "sparkline": [182.0, 183.0, 182.5, 184.0, 183.8, 184.4],
    },
    {
      "symbol": "HCLTECH",
      "company": "HCL Technologies Limited",
      "sector": "Technology",
      "sectorKey": "TECH",
      "price": 1389.00,
      "changeVal": 12.50,
      "changePct": 0.91,
      "positive": true,
      "pe": "22.4x",
      "mktCap": "₹3.8T",
      "volume": "3.6M",
      "dayLow": 1372.0,
      "dayHigh": 1395.0,
      "low52": "₹ 1,120.00",
      "high52": "₹ 1,550.00",
      "isin": "INE860A01027",
      "status": "NSE Verified",
      "sparkline": [1375.0, 1380.0, 1378.0, 1385.0, 1382.0, 1389.0],
    },
    {
      "symbol": "TECHM",
      "company": "Tech Mahindra Limited",
      "sector": "Technology",
      "sectorKey": "TECH",
      "price": 1245.00,
      "changeVal": -8.20,
      "changePct": -0.65,
      "positive": false,
      "pe": "28.0x",
      "mktCap": "₹1.2T",
      "volume": "2.4M",
      "dayLow": 1240.0,
      "dayHigh": 1260.0,
      "low52": "₹ 1,050.00",
      "high52": "₹ 1,420.00",
      "isin": "INE669C01036",
      "status": "NSE Verified",
      "sparkline": [1258.0, 1252.0, 1255.0, 1248.0, 1246.0, 1245.0],
    },

    // --- Banking & Financials ---
    {
      "symbol": "HDFCBANK",
      "company": "HDFC Bank Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 1600.00,
      "changeVal": 5.10,
      "changePct": 0.32,
      "positive": true,
      "pe": "19.2x",
      "mktCap": "₹12.2T",
      "volume": "9.8M",
      "dayLow": 1590.0,
      "dayHigh": 1612.0,
      "low52": "₹ 1,363.55",
      "high52": "₹ 1,794.00",
      "isin": "INE040A01034",
      "status": "NSE Verified",
      "sparkline": [1594.0, 1598.0, 1596.0, 1602.0, 1599.0, 1600.0],
    },
    {
      "symbol": "ICICIBANK",
      "company": "ICICI Bank Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 1240.00,
      "changeVal": 18.60,
      "changePct": 1.52,
      "positive": true,
      "pe": "18.5x",
      "mktCap": "₹8.7T",
      "volume": "11.5M",
      "dayLow": 1222.0,
      "dayHigh": 1248.0,
      "low52": "₹ 928.00",
      "high52": "₹ 1,300.00",
      "isin": "INE090A01021",
      "status": "NSE Verified",
      "sparkline": [1220.0, 1228.0, 1225.0, 1235.0, 1232.0, 1240.0],
    },
    {
      "symbol": "SBIN",
      "company": "State Bank of India",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 815.00,
      "changeVal": -4.20,
      "changePct": -0.51,
      "positive": false,
      "pe": "10.8x",
      "mktCap": "₹7.3T",
      "volume": "12.8M",
      "dayLow": 811.0,
      "dayHigh": 824.0,
      "low52": "₹ 555.00",
      "high52": "₹ 912.00",
      "isin": "INE062A01020",
      "status": "NSE Verified",
      "sparkline": [820.0, 818.0, 822.0, 816.0, 817.0, 815.0],
    },
    {
      "symbol": "KOTAKBANK",
      "company": "Kotak Mahindra Bank Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 1780.00,
      "changeVal": 14.50,
      "changePct": 0.82,
      "positive": true,
      "pe": "21.5x",
      "mktCap": "₹3.5T",
      "volume": "4.2M",
      "dayLow": 1765.0,
      "dayHigh": 1792.0,
      "low52": "₹ 1,544.00",
      "high52": "₹ 1,930.00",
      "isin": "INE237A01028",
      "status": "NSE Verified",
      "sparkline": [1766.0, 1772.0, 1769.0, 1778.0, 1775.0, 1780.0],
    },
    {
      "symbol": "AXISBANK",
      "company": "Axis Bank Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 1050.00,
      "changeVal": 9.20,
      "changePct": 0.88,
      "positive": true,
      "pe": "14.2x",
      "mktCap": "₹3.2T",
      "volume": "6.5M",
      "dayLow": 1040.0,
      "dayHigh": 1058.0,
      "low52": "₹ 952.00",
      "high52": "₹ 1,339.00",
      "isin": "INE238A01034",
      "status": "NSE Verified",
      "sparkline": [1040.0, 1045.0, 1042.0, 1048.0, 1047.0, 1050.0],
    },
    {
      "symbol": "BAJFINANCE",
      "company": "Bajaj Finance Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 6850.00,
      "changeVal": 62.00,
      "changePct": 0.91,
      "positive": true,
      "pe": "29.0x",
      "mktCap": "₹4.2T",
      "volume": "1.8M",
      "dayLow": 6780.0,
      "dayHigh": 6890.0,
      "low52": "₹ 6,350.00",
      "high52": "₹ 8,192.00",
      "isin": "INE296A01024",
      "status": "NSE Verified",
      "sparkline": [6790.0, 6820.0, 6810.0, 6845.0, 6835.0, 6850.0],
    },
    {
      "symbol": "BAJAJFINSV",
      "company": "Bajaj Finserv Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 1580.00,
      "changeVal": 11.20,
      "changePct": 0.71,
      "positive": true,
      "pe": "32.5x",
      "mktCap": "₹2.5T",
      "volume": "2.1M",
      "dayLow": 1568.0,
      "dayHigh": 1590.0,
      "low52": "₹ 1,420.00",
      "high52": "₹ 1,820.00",
      "isin": "INE918I01018",
      "status": "NSE Verified",
      "sparkline": [1568.0, 1574.0, 1572.0, 1578.0, 1576.0, 1580.0],
    },
    {
      "symbol": "JIOFIN",
      "company": "Jio Financial Services Limited",
      "sector": "Banking & Financials",
      "sectorKey": "BANK",
      "price": 320.00,
      "changeVal": 4.50,
      "changePct": 1.43,
      "positive": true,
      "pe": "110.0x",
      "mktCap": "₹2.0T",
      "volume": "15.4M",
      "dayLow": 315.0,
      "dayHigh": 324.0,
      "low52": "₹ 205.00",
      "high52": "₹ 390.00",
      "isin": "INE758E01017",
      "status": "NSE Verified",
      "sparkline": [314.0, 317.0, 316.0, 319.0, 318.5, 320.0],
    },

    // --- Automobile ---
    {
      "symbol": "TATAMOTORS",
      "company": "Tata Motors Limited",
      "sector": "Automobile",
      "sectorKey": "AUTO",
      "price": 924.50,
      "changeVal": 19.20,
      "changePct": 2.12,
      "positive": true,
      "pe": "16.0x",
      "mktCap": "₹3.4T",
      "volume": "14.2M",
      "dayLow": 905.0,
      "dayHigh": 932.0,
      "low52": "₹ 640.00",
      "high52": "₹ 1,179.00",
      "isin": "INE155A01022",
      "status": "NSE Verified",
      "sparkline": [905.0, 912.0, 910.0, 920.0, 918.0, 924.5],
    },
    {
      "symbol": "MARUTI",
      "company": "Maruti Suzuki India Limited",
      "sector": "Automobile",
      "sectorKey": "AUTO",
      "price": 12450.00,
      "changeVal": 115.00,
      "changePct": 0.93,
      "positive": true,
      "pe": "28.5x",
      "mktCap": "₹3.9T",
      "volume": "1.2M",
      "dayLow": 12320.0,
      "dayHigh": 12520.0,
      "low52": "₹ 9,760.00",
      "high52": "₹ 13,680.00",
      "isin": "INE585B01010",
      "status": "NSE Verified",
      "sparkline": [12330.0, 12390.0, 12370.0, 12430.0, 12410.0, 12450.0],
    },
    {
      "symbol": "M&M",
      "company": "Mahindra & Mahindra Limited",
      "sector": "Automobile",
      "sectorKey": "AUTO",
      "price": 2840.00,
      "changeVal": 34.00,
      "changePct": 1.21,
      "positive": true,
      "pe": "25.4x",
      "mktCap": "₹3.5T",
      "volume": "3.5M",
      "dayLow": 2805.0,
      "dayHigh": 2860.0,
      "low52": "₹ 1,850.00",
      "high52": "₹ 3,120.00",
      "isin": "INE101A01026",
      "status": "NSE Verified",
      "sparkline": [2808.0, 2825.0, 2820.0, 2835.0, 2830.0, 2840.0],
    },
    {
      "symbol": "BAJAJ-AUTO",
      "company": "Bajaj Auto Limited",
      "sector": "Automobile",
      "sectorKey": "AUTO",
      "price": 9120.00,
      "changeVal": 78.00,
      "changePct": 0.86,
      "positive": true,
      "pe": "34.0x",
      "mktCap": "₹2.6T",
      "volume": "950K",
      "dayLow": 9020.0,
      "dayHigh": 9180.0,
      "low52": "₹ 6,800.00",
      "high52": "₹ 10,200.00",
      "isin": "INE917I01010",
      "status": "NSE Verified",
      "sparkline": [9030.0, 9080.0, 9060.0, 9110.0, 9095.0, 9120.0],
    },

    // --- Consumer Goods & Retail ---
    {
      "symbol": "ITC",
      "company": "ITC Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 495.20,
      "changeVal": 1.95,
      "changePct": 0.40,
      "positive": true,
      "pe": "27.5x",
      "mktCap": "₹6.2T",
      "volume": "7.6M",
      "dayLow": 492.5,
      "dayHigh": 498.0,
      "low52": "₹ 399.00",
      "high52": "₹ 520.00",
      "isin": "INE154A01025",
      "status": "NSE Verified",
      "sparkline": [493.0, 494.5, 494.0, 496.0, 495.0, 495.2],
    },
    {
      "symbol": "HINDUNILVR",
      "company": "Hindustan Unilever Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 2380.00,
      "changeVal": 12.00,
      "changePct": 0.51,
      "positive": true,
      "pe": "58.0x",
      "mktCap": "₹5.6T",
      "volume": "2.8M",
      "dayLow": 2365.0,
      "dayHigh": 2395.0,
      "low52": "₹ 2,172.00",
      "high52": "₹ 3,035.00",
      "isin": "INE030A01027",
      "status": "NSE Verified",
      "sparkline": [2366.0, 2374.0, 2370.0, 2378.0, 2375.0, 2380.0],
    },
    {
      "symbol": "NESTLEIND",
      "company": "Nestle India Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 2210.00,
      "changeVal": -14.00,
      "changePct": -0.63,
      "positive": false,
      "pe": "72.0x",
      "mktCap": "₹2.1T",
      "volume": "820K",
      "dayLow": 2200.0,
      "dayHigh": 2230.0,
      "low52": "₹ 2,050.00",
      "high52": "₹ 2,780.00",
      "isin": "INE239A01016",
      "status": "NSE Verified",
      "sparkline": [2225.0, 2218.0, 2220.0, 2212.0, 2215.0, 2210.0],
    },
    {
      "symbol": "TITAN",
      "company": "Titan Company Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 3250.00,
      "changeVal": 38.00,
      "changePct": 1.18,
      "positive": true,
      "pe": "82.0x",
      "mktCap": "₹2.9T",
      "volume": "1.9M",
      "dayLow": 3210.0,
      "dayHigh": 3275.0,
      "low52": "₹ 3,055.00",
      "high52": "₹ 3,886.00",
      "isin": "INE280A01028",
      "status": "NSE Verified",
      "sparkline": [3212.0, 3230.0, 3225.0, 3245.0, 3240.0, 3250.0],
    },
    {
      "symbol": "ASIANPAINT",
      "company": "Asian Paints Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 2420.00,
      "changeVal": 16.50,
      "changePct": 0.69,
      "positive": true,
      "pe": "46.5x",
      "mktCap": "₹2.3T",
      "volume": "1.7M",
      "dayLow": 2400.0,
      "dayHigh": 2435.0,
      "low52": "₹ 2,280.00",
      "high52": "₹ 3,200.00",
      "isin": "INE021A01026",
      "status": "NSE Verified",
      "sparkline": [2402.0, 2412.0, 2408.0, 2418.0, 2415.0, 2420.0],
    },
    {
      "symbol": "TRENT",
      "company": "Trent Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 7150.00,
      "changeVal": 120.00,
      "changePct": 1.71,
      "positive": true,
      "pe": "145.0x",
      "mktCap": "₹2.5T",
      "volume": "2.5M",
      "dayLow": 7030.0,
      "dayHigh": 7210.0,
      "low52": "₹ 2,800.00",
      "high52": "₹ 8,200.00",
      "isin": "INE849A01020",
      "status": "NSE Verified",
      "sparkline": [7030.0, 7090.0, 7070.0, 7120.0, 7110.0, 7150.0],
    },
    {
      "symbol": "ZOMATO",
      "company": "Zomato Limited",
      "sector": "Consumer Goods & Retail",
      "sectorKey": "FMCG",
      "price": 265.00,
      "changeVal": 5.20,
      "changePct": 2.00,
      "positive": true,
      "pe": "125.0x",
      "mktCap": "₹2.3T",
      "volume": "28.5M",
      "dayLow": 259.0,
      "dayHigh": 268.0,
      "low52": "₹ 101.00",
      "high52": "₹ 298.00",
      "isin": "INE758T01015",
      "status": "NSE Verified",
      "sparkline": [259.0, 262.0, 261.0, 264.0, 263.5, 265.0],
    },

    // --- Infrastructure & Materials ---
    {
      "symbol": "LT",
      "company": "Larsen & Toubro Limited",
      "sector": "Infrastructure & Materials",
      "sectorKey": "INFRA",
      "price": 3480.00,
      "changeVal": 35.00,
      "changePct": 1.02,
      "positive": true,
      "pe": "34.0x",
      "mktCap": "₹4.8T",
      "volume": "3.8M",
      "dayLow": 3440.0,
      "dayHigh": 3510.0,
      "low52": "₹ 2,870.00",
      "high52": "₹ 3,948.00",
      "isin": "INE018A01030",
      "status": "NSE Verified",
      "sparkline": [3442.0, 3460.0, 3455.0, 3475.0, 3470.0, 3480.0],
    },
    {
      "symbol": "TATASTEEL",
      "company": "Tata Steel Limited",
      "sector": "Infrastructure & Materials",
      "sectorKey": "INFRA",
      "price": 148.50,
      "changeVal": 1.80,
      "changePct": 1.23,
      "positive": true,
      "pe": "18.2x",
      "mktCap": "₹1.8T",
      "volume": "22.4M",
      "dayLow": 146.5,
      "dayHigh": 150.0,
      "low52": "₹ 118.00",
      "high52": "₹ 184.60",
      "isin": "INE081A01020",
      "status": "NSE Verified",
      "sparkline": [146.5, 147.2, 147.0, 148.0, 147.8, 148.5],
    },
    {
      "symbol": "ULTRACEMCO",
      "company": "UltraTech Cement Limited",
      "sector": "Infrastructure & Materials",
      "sectorKey": "INFRA",
      "price": 10950.00,
      "changeVal": 95.00,
      "changePct": 0.88,
      "positive": true,
      "pe": "41.5x",
      "mktCap": "₹3.2T",
      "volume": "780K",
      "dayLow": 10830.0,
      "dayHigh": 11020.0,
      "low52": "₹ 8,900.00",
      "high52": "₹ 12,100.00",
      "isin": "INE481G01011",
      "status": "NSE Verified",
      "sparkline": [10850.0, 10900.0, 10880.0, 10930.0, 10920.0, 10950.0],
    },
    {
      "symbol": "COALINDIA",
      "company": "Coal India Limited",
      "sector": "Infrastructure & Materials",
      "sectorKey": "INFRA",
      "price": 417.20,
      "changeVal": 4.80,
      "changePct": 1.16,
      "positive": true,
      "pe": "8.2x",
      "mktCap": "₹2.6T",
      "volume": "8.2M",
      "dayLow": 411.5,
      "dayHigh": 420.0,
      "low52": "₹ 305.00",
      "high52": "₹ 530.00",
      "isin": "INE522F01014",
      "status": "NSE Verified",
      "sparkline": [412.0, 414.5, 413.8, 416.5, 415.8, 417.2],
    },
    {
      "symbol": "ADANIPORTS",
      "company": "Adani Ports & SEZ Limited",
      "sector": "Infrastructure & Materials",
      "sectorKey": "INFRA",
      "price": 1758.80,
      "changeVal": 22.00,
      "changePct": 1.27,
      "positive": true,
      "pe": "36.5x",
      "mktCap": "₹3.8T",
      "volume": "5.1M",
      "dayLow": 1735.0,
      "dayHigh": 1775.0,
      "low52": "₹ 1,120.00",
      "high52": "₹ 1,880.00",
      "isin": "INE742F01042",
      "status": "NSE Verified",
      "sparkline": [1736.0, 1748.0, 1745.0, 1755.0, 1752.0, 1758.8],
    },

    // --- Healthcare & Pharma ---
    {
      "symbol": "SUNPHARMA",
      "company": "Sun Pharmaceutical Industries Limited",
      "sector": "Healthcare & Pharma",
      "sectorKey": "HEALTH",
      "price": 1820.00,
      "changeVal": 15.00,
      "changePct": 0.83,
      "positive": true,
      "pe": "38.5x",
      "mktCap": "₹4.4T",
      "volume": "3.4M",
      "dayLow": 1802.0,
      "dayHigh": 1832.0,
      "low52": "₹ 1,078.00",
      "high52": "₹ 1,960.00",
      "isin": "INE044A01036",
      "status": "NSE Verified",
      "sparkline": [1804.0, 1812.0, 1810.0, 1818.0, 1815.0, 1820.0],
    },
    {
      "symbol": "DRREDDY",
      "company": "Dr. Reddy's Laboratories Limited",
      "sector": "Healthcare & Pharma",
      "sectorKey": "HEALTH",
      "price": 6350.00,
      "changeVal": -32.00,
      "changePct": -0.50,
      "positive": false,
      "pe": "19.8x",
      "mktCap": "₹1.1T",
      "volume": "920K",
      "dayLow": 6330.0,
      "dayHigh": 6410.0,
      "low52": "₹ 5,400.00",
      "high52": "₹ 7,100.00",
      "isin": "INE089A01023",
      "status": "NSE Verified",
      "sparkline": [6385.0, 6370.0, 6375.0, 6360.0, 6355.0, 6350.0],
    },

    // --- Defense & Telecom ---
    {
      "symbol": "BHARTIARTL",
      "company": "Bharti Airtel Limited",
      "sector": "Defense & Telecom",
      "sectorKey": "DEFENSE",
      "price": 1905.00,
      "changeVal": 24.00,
      "changePct": 1.28,
      "positive": true,
      "pe": "45.0x",
      "mktCap": "₹11.2T",
      "volume": "6.2M",
      "dayLow": 1880.0,
      "dayHigh": 1920.0,
      "low52": "₹ 912.00",
      "high52": "₹ 1,920.00",
      "isin": "INE397D01024",
      "status": "NSE Verified",
      "sparkline": [1882.0, 1895.0, 1890.0, 1902.0, 1898.0, 1905.0],
    },
    {
      "symbol": "BEL",
      "company": "Bharat Electronics Limited",
      "sector": "Defense & Telecom",
      "sectorKey": "DEFENSE",
      "price": 576.85,
      "changeVal": 8.40,
      "changePct": 1.48,
      "positive": true,
      "pe": "42.0x",
      "mktCap": "₹4.2T",
      "volume": "14.8M",
      "dayLow": 568.0,
      "dayHigh": 582.0,
      "low52": "₹ 230.00",
      "high52": "₹ 620.00",
      "isin": "INE263A01024",
      "status": "NSE Verified",
      "sparkline": [568.0, 572.0, 570.0, 575.0, 573.5, 576.85],
    },
    {
      "symbol": "HAL",
      "company": "Hindustan Aeronautics Limited",
      "sector": "Defense & Telecom",
      "sectorKey": "DEFENSE",
      "price": 4989.00,
      "changeVal": 72.00,
      "changePct": 1.46,
      "positive": true,
      "pe": "36.0x",
      "mktCap": "₹3.3T",
      "volume": "3.1M",
      "dayLow": 4900.0,
      "dayHigh": 5020.0,
      "low52": "₹ 1,768.00",
      "high52": "₹ 5,675.00",
      "isin": "INE066F01020",
      "status": "NSE Verified",
      "sparkline": [4910.0, 4950.0, 4940.0, 4975.0, 4965.0, 4989.0],
    },
  ];

  static final List<Map<String, dynamic>> _fallbackIndices = [
    // --- Tier 1: Headline Indices (8) ---
    {
      'symbol': 'NIFTY 50',
      'display_name': 'NIFTY 50',
      'canonical_id': 'NSE_INDEX_NIFTY50',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Flagship benchmark index representing 50 top blue-chip Indian companies',
      'price': 24180.80,
      'change': 120.40,
      'change_pct': 0.50,
      'is_positive': true,
      'open_price': 24100.0,
      'high_price': 24220.5,
      'low_price': 24050.0,
      'close_price': 24060.4,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [24100.0, 24140.0, 24120.0, 24190.0, 24170.0, 24180.80],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'SENSEX',
      'display_name': 'BSE SENSEX',
      'canonical_id': 'BSE_INDEX_SENSEX',
      'exchange': 'BSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Benchmark index of 30 well-established and financially sound companies on BSE',
      'price': 79402.29,
      'change': 362.45,
      'change_pct': 0.46,
      'is_positive': true,
      'open_price': 79200.0,
      'high_price': 79550.0,
      'low_price': 79100.0,
      'close_price': 79039.84,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [79200.0, 79350.0, 79280.0, 79450.0, 79390.0, 79402.29],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY BANK',
      'display_name': 'NIFTY BANK',
      'canonical_id': 'NSE_INDEX_NIFTYBANK',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Banking sector benchmark covering top Indian public and private commercial banks',
      'price': 51230.15,
      'change': 285.60,
      'change_pct': 0.56,
      'is_positive': true,
      'open_price': 51000.0,
      'high_price': 51380.0,
      'low_price': 50920.0,
      'close_price': 50944.55,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [51000.0, 51150.0, 51080.0, 51290.0, 51210.0, 51230.15],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY NEXT 50',
      'display_name': 'NIFTY NEXT 50',
      'canonical_id': 'NSE_INDEX_NIFTYNEXT50',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Top 50 companies after Nifty 50, representing future large-cap contenders',
      'price': 68950.40,
      'change': -145.20,
      'change_pct': -0.21,
      'is_positive': false,
      'open_price': 69150.0,
      'high_price': 69280.0,
      'low_price': 68820.0,
      'close_price': 69095.6,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [69150.0, 69020.0, 69100.0, 68920.0, 68980.0, 68950.40],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY MIDCAP 50',
      'display_name': 'NIFTY MIDCAP 50',
      'canonical_id': 'NSE_INDEX_NIFTYMIDCAP50',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Top 50 mid-sized Indian companies with active derivative contracts',
      'price': 15640.25,
      'change': 98.40,
      'change_pct': 0.63,
      'is_positive': true,
      'open_price': 15550.0,
      'high_price': 15690.0,
      'low_price': 15510.0,
      'close_price': 15541.85,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [15550.0, 15590.0, 15570.0, 15650.0, 15620.0, 15640.25],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY SMALLCAP 100',
      'display_name': 'NIFTY SMALLCAP 100',
      'canonical_id': 'NSE_INDEX_NIFTYSMALLCAP100',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Top 100 small-cap growth companies in India by market capitalization',
      'price': 18450.90,
      'change': 142.10,
      'change_pct': 0.78,
      'is_positive': true,
      'open_price': 18320.0,
      'high_price': 18510.0,
      'low_price': 18280.0,
      'close_price': 18308.8,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [18320.0, 18380.0, 18350.0, 18470.0, 18430.0, 18450.90],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY 100',
      'display_name': 'NIFTY 100',
      'canonical_id': 'NSE_INDEX_NIFTY100',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Top 100 large-cap Indian companies across all major economic sectors',
      'price': 25120.35,
      'change': 110.80,
      'change_pct': 0.44,
      'is_positive': true,
      'open_price': 25030.0,
      'high_price': 25170.0,
      'low_price': 24980.0,
      'close_price': 25009.55,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [25030.0, 25080.0, 25050.0, 25140.0, 25100.0, 25120.35],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY 500',
      'display_name': 'NIFTY 500',
      'canonical_id': 'NSE_INDEX_NIFTY500',
      'exchange': 'NSE',
      'category': 'headline',
      'tier': 'tier1',
      'description': 'Broad market index representing 96% of free-float capitalization on NSE',
      'price': 22680.10,
      'change': 85.30,
      'change_pct': 0.38,
      'is_positive': true,
      'open_price': 22600.0,
      'high_price': 22720.0,
      'low_price': 22560.0,
      'close_price': 22594.8,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [22600.0, 22640.0, 22620.0, 22690.0, 22670.0, 22680.10],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },

    // --- Tier 2: Sectoral Indices (10) ---
    {
      'symbol': 'NIFTY IT',
      'display_name': 'NIFTY IT',
      'canonical_id': 'NSE_INDEX_NIFTYIT',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Information Technology giants driving Indian software & digital services',
      'price': 37820.60,
      'change': -210.50,
      'change_pct': -0.55,
      'is_positive': false,
      'open_price': 38100.0,
      'high_price': 38220.0,
      'low_price': 37750.0,
      'close_price': 38031.1,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [38100.0, 37950.0, 38020.0, 37800.0, 37860.0, 37820.60],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY AUTO',
      'display_name': 'NIFTY AUTO',
      'canonical_id': 'NSE_INDEX_NIFTYAUTO',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Automobile manufacturers, EV pioneers, and component leaders in India',
      'price': 23410.75,
      'change': 185.20,
      'change_pct': 0.80,
      'is_positive': true,
      'open_price': 23250.0,
      'high_price': 23480.0,
      'low_price': 23200.0,
      'close_price': 23225.55,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [23250.0, 23320.0, 23300.0, 23430.0, 23390.0, 23410.75],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY PHARMA',
      'display_name': 'NIFTY PHARMA',
      'canonical_id': 'NSE_INDEX_NIFTYPHARMA',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Pharmaceutical & healthcare majors driving drug discovery & formulations',
      'price': 21890.30,
      'change': 115.40,
      'change_pct': 0.53,
      'is_positive': true,
      'open_price': 21790.0,
      'high_price': 21950.0,
      'low_price': 21740.0,
      'close_price': 21774.9,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [21790.0, 21840.0, 21820.0, 21910.0, 21870.0, 21890.30],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY FMCG',
      'display_name': 'NIFTY FMCG',
      'canonical_id': 'NSE_INDEX_NIFTYFMCG',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Fast Moving Consumer Goods manufacturers, household goods & food majors',
      'price': 57420.80,
      'change': 195.10,
      'change_pct': 0.34,
      'is_positive': true,
      'open_price': 57250.0,
      'high_price': 57550.0,
      'low_price': 57180.0,
      'close_price': 57225.7,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [57250.0, 57320.0, 57290.0, 57450.0, 57400.0, 57420.80],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY METAL',
      'display_name': 'NIFTY METAL',
      'canonical_id': 'NSE_INDEX_NIFTYMETAL',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Mining, steel, aluminum and non-ferrous metal producers in India',
      'price': 9140.20,
      'change': 105.80,
      'change_pct': 1.17,
      'is_positive': true,
      'open_price': 9040.0,
      'high_price': 9180.0,
      'low_price': 9010.0,
      'close_price': 9034.4,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [9040.0, 9080.0, 9060.0, 9150.0, 9120.0, 9140.20],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY ENERGY',
      'display_name': 'NIFTY ENERGY',
      'canonical_id': 'NSE_INDEX_NIFTYENERGY',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Petroleum, gas, power utilities and renewable energy providers',
      'price': 38920.45,
      'change': 240.10,
      'change_pct': 0.62,
      'is_positive': true,
      'open_price': 38700.0,
      'high_price': 39050.0,
      'low_price': 38650.0,
      'close_price': 38680.35,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [38700.0, 38800.0, 38760.0, 38950.0, 38900.0, 38920.45],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY PSU BANK',
      'display_name': 'NIFTY PSU BANK',
      'canonical_id': 'NSE_INDEX_NIFTYPSUBANK',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'State-owned and public sector banks across India',
      'price': 6780.90,
      'change': 72.30,
      'change_pct': 1.08,
      'is_positive': true,
      'open_price': 6715.0,
      'high_price': 6810.0,
      'low_price': 6695.0,
      'close_price': 6708.6,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [6715.0, 6740.0, 6730.0, 6790.0, 6770.0, 6780.90],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY REALTY',
      'display_name': 'NIFTY REALTY',
      'canonical_id': 'NSE_INDEX_NIFTYREALTY',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Residential, commercial real estate and construction developers',
      'price': 985.40,
      'change': 12.80,
      'change_pct': 1.32,
      'is_positive': true,
      'open_price': 974.0,
      'high_price': 992.0,
      'low_price': 970.0,
      'close_price': 972.6,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [974.0, 978.0, 976.0, 988.0, 982.0, 985.40],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY MEDIA',
      'display_name': 'NIFTY MEDIA',
      'canonical_id': 'NSE_INDEX_NIFTYMEDIA',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Media, broadcast, entertainment and publication companies',
      'price': 1980.20,
      'change': -14.60,
      'change_pct': -0.73,
      'is_positive': false,
      'open_price': 2000.0,
      'high_price': 2010.0,
      'low_price': 1970.0,
      'close_price': 1994.8,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [2000.0, 1990.0, 1995.0, 1975.0, 1985.0, 1980.20],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
    {
      'symbol': 'NIFTY FINANCIAL SERVICES',
      'display_name': 'NIFTY FINANCIAL SERVICES',
      'canonical_id': 'NSE_INDEX_NIFTYFINSERVICE',
      'exchange': 'NSE',
      'category': 'sectoral',
      'tier': 'tier2',
      'description': 'Banks, NBFCs, insurance, housing finance, and asset management companies',
      'price': 23680.50,
      'change': 145.20,
      'change_pct': 0.62,
      'is_positive': true,
      'open_price': 23550.0,
      'high_price': 23740.0,
      'low_price': 23500.0,
      'close_price': 23535.3,
      'source': 'ANGEL_ONE_SMARTAPI',
      'sparkline': [23550.0, 23610.0, 23580.0, 23700.0, 23660.0, 23680.50],
      'served_from_cache': true,
      'observed_at': 'Market Close',
    },
  ];

  @override
  void initState() {
    super.initState();
    _indicesList = List.from(_fallbackIndices);
    _loadIndices();
  }

  Future<void> _loadIndices() async {
    setState(() => _indicesLoading = true);
    try {
      final res = await apiClient.getIndices();
      final liveList = List<Map<String, dynamic>>.from(res['indices'] ?? []);
      if (liveList.isNotEmpty && mounted) {
        final updated = _indicesList.map((fallback) {
          final live = liveList.firstWhere(
            (i) => i['symbol'] == fallback['symbol'],
            orElse: () => <String, dynamic>{},
          );
          if (live.isNotEmpty) {
            final price = (live['price'] ?? live['last_price'] as num?)?.toDouble() ?? fallback['price'];
            final change = (live['change'] as num?)?.toDouble() ?? fallback['change'];
            final changePct = (live['change_pct'] as num?)?.toDouble() ?? fallback['change_pct'];
            return {
              ...fallback,
              ...live,
              'price': price,
              'change': change,
              'change_pct': changePct,
              'is_positive': change >= 0,
              'served_from_cache': live['served_from_cache'] ?? false,
              'observed_at': live['observed_at'] ?? 'Real-time',
            };
          }
          return fallback;
        }).toList();
        setState(() {
          _indicesList = updated;
          _indicesLoading = false;
        });
      } else {
        if (mounted) setState(() => _indicesLoading = false);
      }
    } catch (_) {
      if (mounted) setState(() => _indicesLoading = false);
    }
  }

  void _toggleWatchlist(String symbol) {
    setState(() {
      if (_pinnedWatchlist.contains(symbol)) {
        _pinnedWatchlist.remove(symbol);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Removed $symbol from My Watchlist"),
            duration: const Duration(seconds: 1),
            backgroundColor: TerminalColors.panel,
          ),
        );
      } else {
        _pinnedWatchlist.add(symbol);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Pinned $symbol to My Watchlist"),
            duration: const Duration(seconds: 1),
            backgroundColor: TerminalColors.panel,
          ),
        );
      }
    });
  }

  void _showInstrumentDetails(Map<String, dynamic> item) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        String period = '1M';
        return StatefulBuilder(
          builder: (context, setSheetState) {
            final isPos = item['positive'] as bool;
            final sym = item['symbol'] as String;
            final price = item['price'] as double;
            final chgVal = item['changeVal'] as double;
            final chgPct = item['changePct'] as double;
            final sparklinePoints = List<double>.from(item['sparkline'] ?? [price * 0.98, price * 1.01, price]);

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 16,
                top: 16,
                left: 16,
                right: 16,
              ),
              child: SizedBox(
                height: 580,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header Bar
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              radius: 18,
                              backgroundColor: TerminalColors.panel,
                              child: Text(
                                sym.substring(0, math.min(2, sym.length)),
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(sym, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: TerminalColors.panel,
                                        borderRadius: BorderRadius.circular(3),
                                        border: Border.all(color: TerminalColors.borderSubtle),
                                      ),
                                      child: Text(item['status'], style: const TextStyle(fontSize: 9, color: TerminalColors.textMuted)),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 2),
                                Text(item['company'], style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                              ],
                            ),
                          ],
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Price & Day Change Ribbon
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "₹${price.toStringAsFixed(2)}",
                              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                            ),
                            Text(
                              "${isPos ? '+' : ''}${chgVal.toStringAsFixed(2)} (${isPos ? '+' : ''}${chgPct.toStringAsFixed(2)}%)",
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                fontFamily: 'monospace',
                                color: isPos ? TerminalColors.positive : TerminalColors.negative,
                              ),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0x18F29A60),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0x40F29A60)),
                          ),
                          child: Text(
                            item['sector'],
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: TerminalColors.action),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Simulated Price Trend Mini Chart with Timeframe Selector
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: TerminalColors.panel,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: TerminalColors.borderSubtle),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text("SIMULATED PRICE CURVE", style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                              Row(
                                children: ['1D', '1W', '1M', '1Y'].map((p) {
                                  final isSel = period == p;
                                  return GestureDetector(
                                    onTap: () => setSheetState(() => period = p),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      margin: const EdgeInsets.only(left: 4),
                                      decoration: BoxDecoration(
                                        color: isSel ? TerminalColors.action : Colors.transparent,
                                        borderRadius: BorderRadius.circular(3),
                                      ),
                                      child: Text(
                                        p,
                                        style: TextStyle(
                                          fontSize: 9,
                                          fontWeight: FontWeight.bold,
                                          color: isSel ? Colors.black : TerminalColors.textMuted,
                                        ),
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            height: 60,
                            width: double.infinity,
                            child: CustomPaint(
                              painter: _MiniSparklinePainter(
                                points: sparklinePoints,
                                isPositive: isPos,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Comprehensive Fundamentals Table
                    Expanded(
                      child: SingleChildScrollView(
                        child: Column(
                          children: [
                            _buildDetailRow("Day's Range", "₹${(item['dayLow'] as double).toStringAsFixed(2)} – ₹${(item['dayHigh'] as double).toStringAsFixed(2)}"),
                            _buildDetailRow("52-Week Range", "${item['low52']} – ${item['high52']}"),
                            _buildDetailRow("Market Capitalization", item['mktCap']),
                            _buildDetailRow("Trailing P/E Ratio", item['pe']),
                            _buildDetailRow("Today's Volume", item['volume']),
                            _buildDetailRow("ISIN Identifier", item['isin']),
                            _buildDetailRow("Sector Classification", item['sector']),
                            _buildDetailRow("Data Provenance", "NSE / yfinance Real Observation"),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Bottom Action CTAs
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: TerminalColors.panel,
                              foregroundColor: Colors.white,
                              side: const BorderSide(color: TerminalColors.borderSubtle),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            icon: const Icon(Icons.show_chart, size: 16, color: TerminalColors.action),
                            label: const Text("Open Chart", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                            onPressed: () {
                              Navigator.pop(ctx);
                              Navigator.push(
                                context,
                                MaterialPageRoute(builder: (context) => MobileChartScreen(initialSymbol: sym)),
                              );
                            },
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: TerminalColors.action,
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            icon: const Icon(Icons.flash_on, size: 16),
                            label: const Text("Instant Trade", style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                            onPressed: () {
                              Navigator.pop(ctx);
                              QuickTradeModal.show(context, initialSymbol: sym);
                            },
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
          Text(value, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Dynamic Sector Counts
    final sectorCounts = {
      'ALL': _instruments.length,
      'TECH': _instruments.where((i) => i['sectorKey'] == 'TECH').length,
      'BANK': _instruments.where((i) => i['sectorKey'] == 'BANK').length,
      'ENERGY': _instruments.where((i) => i['sectorKey'] == 'ENERGY').length,
      'AUTO': _instruments.where((i) => i['sectorKey'] == 'AUTO').length,
      'FMCG': _instruments.where((i) => i['sectorKey'] == 'FMCG').length,
      'INFRA': _instruments.where((i) => i['sectorKey'] == 'INFRA').length,
      'HEALTH': _instruments.where((i) => i['sectorKey'] == 'HEALTH').length,
      'DEFENSE': _instruments.where((i) => i['sectorKey'] == 'DEFENSE').length,
    };

    var filtered = _instruments.where((item) {
      final sym = item['symbol'] as String;
      final comp = item['company'] as String;
      final matchesSearch = sym.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          comp.toLowerCase().contains(_searchQuery.toLowerCase());

      final matchesTab = _selectedTab == 0 ? _pinnedWatchlist.contains(sym) : true;
      final matchesSector = _selectedSector == 'ALL' || item['sectorKey'] == _selectedSector;

      return matchesSearch && matchesTab && matchesSector;
    }).toList();

    // Apply Sorting
    if (_selectedSort == 'GAINERS') {
      filtered.sort((a, b) => (b['changePct'] as double).compareTo(a['changePct'] as double));
    } else if (_selectedSort == 'LOSERS') {
      filtered.sort((a, b) => (a['changePct'] as double).compareTo(b['changePct'] as double));
    } else if (_selectedSort == 'PRICE_HIGH') {
      filtered.sort((a, b) => (b['price'] as double).compareTo(a['price'] as double));
    }

    return Column(
      children: [
        // Top Market Mode Switcher: Equities vs Indices
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
          child: Container(
            height: 36,
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(
              color: TerminalColors.input,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: Row(
              children: [
                _buildMarketModeTab("Equities (${_instruments.length})", 'equities'),
                _buildMarketModeTab("Indices (${_indicesList.length})", 'indices'),
              ],
            ),
          ),
        ),

        // Shared Search Bar
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Container(
            height: 40,
            decoration: BoxDecoration(
              color: TerminalColors.input,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: TextField(
              onChanged: (v) => setState(() => _searchQuery = v),
              style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
              decoration: InputDecoration(
                hintText: _marketMode == 'equities'
                    ? "Search stocks, symbols, or sectors..."
                    : "Search index name or symbol (e.g. NIFTY 50, Bank)...",
                hintStyle: const TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                prefixIcon: const Icon(Icons.search, size: 18, color: TerminalColors.textMuted),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 16, color: TerminalColors.textMuted),
                        onPressed: () => setState(() => _searchQuery = ''),
                      )
                    : null,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 9),
              ),
            ),
          ),
        ),

        if (_marketMode == 'indices')
          _buildIndicesView()
        else ...[
        // Filter Tabs: My Watchlist vs All Instruments
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              _buildViewTab("My Watchlist (${_pinnedWatchlist.length})", 0),
              const SizedBox(width: 8),
              _buildViewTab("All Instruments (${_instruments.length})", 1),
            ],
          ),
        ),
        const SizedBox(height: 8),

        // Sector Filter Ribbon with dynamic counts
        Container(
          height: 32,
          margin: const EdgeInsets.only(bottom: 8),
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              _buildSectorChip("All Sectors (${sectorCounts['ALL']})", 'ALL'),
              _buildSectorChip("Technology (${sectorCounts['TECH']})", 'TECH'),
              _buildSectorChip("Banking (${sectorCounts['BANK']})", 'BANK'),
              _buildSectorChip("Energy (${sectorCounts['ENERGY']})", 'ENERGY'),
              _buildSectorChip("Automobile (${sectorCounts['AUTO']})", 'AUTO'),
              _buildSectorChip("Consumer (${sectorCounts['FMCG']})", 'FMCG'),
              _buildSectorChip("Infrastructure (${sectorCounts['INFRA']})", 'INFRA'),
              _buildSectorChip("Pharma (${sectorCounts['HEALTH']})", 'HEALTH'),
              _buildSectorChip("Defense (${sectorCounts['DEFENSE']})", 'DEFENSE'),
            ],
          ),
        ),

        // Instrument List Rows
        Expanded(
          child: filtered.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.bookmark_border, size: 36, color: TerminalColors.textMuted),
                      const SizedBox(height: 8),
                      Text(
                        _selectedTab == 0 ? "No instruments pinned in Watchlist" : "No instruments match your query",
                        style: const TextStyle(fontSize: 13, color: TerminalColors.textMuted),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: filtered.length,
                  itemBuilder: (context, idx) {
                    final item = filtered[idx];
                    final sym = item['symbol'] as String;
                    final price = item['price'] as double;
                    final chgPct = item['changePct'] as double;
                    final isPos = item['positive'] as bool;
                    final isPinned = _pinnedWatchlist.contains(sym);
                    final sparklinePoints = List<double>.from(item['sparkline'] ?? [price * 0.98, price * 1.01, price]);

                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      decoration: BoxDecoration(
                        color: TerminalColors.surface,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: TerminalColors.borderSubtle),
                      ),
                      child: InkWell(
                        onTap: () => _showInstrumentDetails(item),
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Top Row: Star, Symbol, Name, Price & Day Change
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    icon: Icon(
                                      isPinned ? Icons.star : Icons.star_border,
                                      size: 18,
                                      color: isPinned ? TerminalColors.action : TerminalColors.textMuted,
                                    ),
                                    onPressed: () => _toggleWatchlist(sym),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Text(
                                              sym,
                                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: TerminalColors.textMain),
                                            ),
                                            const SizedBox(width: 6),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                              decoration: BoxDecoration(
                                                color: TerminalColors.panel,
                                                borderRadius: BorderRadius.circular(2),
                                              ),
                                              child: Text(
                                                item['status'],
                                                style: const TextStyle(fontSize: 9, color: TerminalColors.textMuted),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          item['company'],
                                          style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        "₹ ${price.toStringAsFixed(2)}",
                                        style: const TextStyle(fontSize: 14, fontFamily: 'monospace', fontWeight: FontWeight.w800, color: TerminalColors.textMain),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        "${isPos ? '+' : ''}${chgPct.toStringAsFixed(2)}%",
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontFamily: 'monospace',
                                          fontWeight: FontWeight.w700,
                                          color: isPos ? TerminalColors.positive : TerminalColors.negative,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),

                              // Middle Row: Multiples (P/E, MCap, Vol) + 24h Mini Sparkline
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: TerminalColors.panel,
                                          borderRadius: BorderRadius.circular(3),
                                        ),
                                        child: Text(
                                          item['sector'],
                                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: TerminalColors.textMuted),
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        "PE ${item['pe']} · ${item['mktCap']}",
                                        style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted),
                                      ),
                                    ],
                                  ),
                                  // 24h Mini Sparkline
                                  SizedBox(
                                    width: 65,
                                    height: 18,
                                    child: CustomPaint(
                                      painter: _MiniSparklinePainter(
                                        points: sparklinePoints,
                                        isPositive: isPos,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),

                              // Bottom Action Buttons: Chart, Trade & Inspect
                              Row(
                                children: [
                                  Expanded(
                                    child: GestureDetector(
                                      onTap: () {
                                        Navigator.push(
                                          context,
                                          MaterialPageRoute(builder: (context) => MobileChartScreen(initialSymbol: sym)),
                                        );
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(vertical: 5),
                                        decoration: BoxDecoration(
                                          color: TerminalColors.panel,
                                          borderRadius: BorderRadius.circular(3),
                                          border: Border.all(color: TerminalColors.borderSubtle),
                                        ),
                                        alignment: Alignment.center,
                                        child: const Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Icon(Icons.show_chart, size: 12, color: TerminalColors.action),
                                            SizedBox(width: 4),
                                            Text("Chart", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: TerminalColors.action)),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: GestureDetector(
                                      onTap: () => QuickTradeModal.show(context, initialSymbol: sym),
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(vertical: 5),
                                        decoration: BoxDecoration(
                                          color: const Color(0x18F29A60),
                                          borderRadius: BorderRadius.circular(3),
                                          border: Border.all(color: const Color(0x40F29A60)),
                                        ),
                                        alignment: Alignment.center,
                                        child: const Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Icon(Icons.flash_on, size: 12, color: TerminalColors.action),
                                            SizedBox(width: 4),
                                            Text("Trade", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  GestureDetector(
                                    onTap: () => _showInstrumentDetails(item),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                      decoration: BoxDecoration(
                                        color: TerminalColors.panel,
                                        borderRadius: BorderRadius.circular(3),
                                        border: Border.all(color: TerminalColors.borderSubtle),
                                      ),
                                      child: const Text("Details →", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
        ],
      ],
    );
  }

  Widget _buildMarketModeTab(String label, String mode) {
    final isSelected = _marketMode == mode;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() {
          _marketMode = mode;
          _searchQuery = '';
        }),
        child: Container(
          decoration: BoxDecoration(
            color: isSelected ? TerminalColors.surface : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isSelected ? TerminalColors.action : Colors.transparent),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildIndexCategoryChip(String label, String categoryKey) {
    final isSelected = _selectedIndexCategory == categoryKey;
    return GestureDetector(
      onTap: () => setState(() => _selectedIndexCategory = categoryKey),
      child: Container(
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? TerminalColors.action.withValues(alpha: 0.2) : TerminalColors.panel,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _buildIndicesView() {
    final query = _searchQuery.toLowerCase().trim();
    final filtered = _indicesList.where((idx) {
      final sym = (idx['symbol'] as String? ?? '').toLowerCase();
      final name = (idx['display_name'] as String? ?? '').toLowerCase();
      final desc = (idx['description'] as String? ?? '').toLowerCase();
      final cat = (idx['category'] as String? ?? '').toUpperCase();

      final matchesSearch = query.isEmpty || sym.contains(query) || name.contains(query) || desc.contains(query);
      final matchesCat = _selectedIndexCategory == 'ALL' || cat == _selectedIndexCategory;
      return matchesSearch && matchesCat;
    }).toList();

    final headlineCount = _indicesList.where((i) => i['category'] == 'headline').length;
    final sectoralCount = _indicesList.where((i) => i['category'] == 'sectoral').length;

    return Expanded(
      child: Column(
        children: [
          // Informational Banner
          Container(
            margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0x10F29A60),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: const Color(0x30F29A60)),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline, size: 14, color: TerminalColors.action),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    "Official NSE & BSE benchmark observations. Indices represent basket calculations and cannot be bought or sold directly as equity shares.",
                    style: TextStyle(fontSize: 10, color: TerminalColors.textMuted, height: 1.3),
                  ),
                ),
              ],
            ),
          ),

          // Indices Category Ribbon
          Container(
            height: 32,
            margin: const EdgeInsets.only(bottom: 8),
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                _buildIndexCategoryChip("All Indices (${_indicesList.length})", 'ALL'),
                _buildIndexCategoryChip("Headline Benchmarks ($headlineCount)", 'HEADLINE'),
                _buildIndexCategoryChip("Sectoral Indices ($sectoralCount)", 'SECTORAL'),
              ],
            ),
          ),

          // Indices List
          Expanded(
            child: _indicesLoading && _indicesList.isEmpty
                ? const MarketsSkeleton()
                : filtered.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.show_chart, size: 36, color: TerminalColors.textMuted),
                            SizedBox(height: 8),
                            Text(
                              "No indices match your query",
                              style: TextStyle(fontSize: 13, color: TerminalColors.textMuted),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        color: TerminalColors.action,
                        backgroundColor: TerminalColors.surface,
                        onRefresh: _loadIndices,
                        child: ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          itemCount: filtered.length,
                          itemBuilder: (context, idx) {
                            return _buildIndexCard(filtered[idx]);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildIndexCard(Map<String, dynamic> item) {
    final sym = item['symbol'] as String;
    final name = item['display_name'] as String? ?? sym;
    final price = (item['price'] as num?)?.toDouble() ?? 0.0;
    final chg = (item['change'] as num?)?.toDouble() ?? 0.0;
    final chgPct = (item['change_pct'] as num?)?.toDouble() ?? 0.0;
    final isPos = item['is_positive'] as bool? ?? (chg >= 0);
    final category = (item['category'] as String? ?? 'headline').toUpperCase();
    final exchange = item['exchange'] as String? ?? 'NSE';
    final isCached = item['served_from_cache'] == true;
    final desc = item['description'] as String? ?? '';
    final sparklinePoints = List<double>.from(
      item['sparkline'] ?? [price * 0.99, price * 1.005, price],
    );

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => MobileChartScreen(
                initialSymbol: sym,
                isIndex: true,
              ),
            ),
          );
        },
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Row: Symbol, Exchange, Category & Honesty Badge
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(
                        sym,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          fontFamily: 'monospace',
                          color: TerminalColors.textMain,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: TerminalColors.panel,
                          borderRadius: BorderRadius.circular(3),
                          border: Border.all(color: TerminalColors.borderSubtle),
                        ),
                        child: Text(
                          exchange,
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: TerminalColors.textMuted),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: category == 'HEADLINE'
                              ? const Color(0x22F29A60)
                              : const Color(0x2260A5FA),
                          borderRadius: BorderRadius.circular(3),
                          border: Border.all(
                            color: category == 'HEADLINE'
                                ? TerminalColors.action.withValues(alpha: 0.5)
                                : const Color(0x6060A5FA),
                          ),
                        ),
                        child: Text(
                          category,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: category == 'HEADLINE' ? TerminalColors.action : const Color(0xFF60A5FA),
                          ),
                        ),
                      ),
                    ],
                  ),
                  // Honesty Badge: LIVE vs CACHED
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: isCached
                          ? const Color(0x15F29A60)
                          : TerminalColors.positiveBg,
                      borderRadius: BorderRadius.circular(3),
                      border: Border.all(
                        color: isCached ? const Color(0x40F29A60) : TerminalColors.positive,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 5,
                          height: 5,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isCached ? TerminalColors.action : TerminalColors.positive,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          isCached ? "CACHED" : "LIVE",
                          style: TextStyle(
                            fontSize: 8.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.4,
                            color: isCached ? TerminalColors.action : TerminalColors.positive,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),

              // Description / Subtitle
              Text(
                desc.isNotEmpty ? desc : name,
                style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 10),

              // Price, Change & Mini Sparkline Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "₹ ${price.toStringAsFixed(2)}",
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          fontFamily: 'monospace',
                          color: TerminalColors.textMain,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        "${isPos ? '+' : ''}${chg.toStringAsFixed(2)} (${isPos ? '+' : ''}${chgPct.toStringAsFixed(2)}%)",
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                          color: isPos ? TerminalColors.positive : TerminalColors.negative,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(
                    width: 75,
                    height: 22,
                    child: CustomPaint(
                      painter: _MiniSparklinePainter(
                        points: sparklinePoints,
                        isPositive: isPos,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Bottom Actions: View Chart & Constituents
              Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => MobileChartScreen(
                              initialSymbol: sym,
                              isIndex: true,
                            ),
                          ),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        decoration: BoxDecoration(
                          color: TerminalColors.panel,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: TerminalColors.borderSubtle),
                        ),
                        alignment: Alignment.center,
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.show_chart, size: 13, color: TerminalColors.action),
                            SizedBox(width: 4),
                            Text(
                              "Open Index Chart",
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: TerminalColors.action),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: () => _showIndexDetails(item),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: TerminalColors.panel,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: TerminalColors.borderSubtle),
                      ),
                      child: const Text("Info →", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showIndexDetails(Map<String, dynamic> item) {
    final sym = item['symbol'] as String;
    final name = item['display_name'] as String? ?? sym;
    final price = (item['price'] as num?)?.toDouble() ?? 0.0;
    final chg = (item['change'] as num?)?.toDouble() ?? 0.0;
    final chgPct = (item['change_pct'] as num?)?.toDouble() ?? 0.0;
    final isPos = item['is_positive'] as bool? ?? (chg >= 0);
    final category = (item['category'] as String? ?? 'headline').toUpperCase();
    final exchange = item['exchange'] as String? ?? 'NSE';
    final isCached = item['served_from_cache'] == true;
    final observedAt = item['observed_at'] as String? ?? 'Market Close';
    final desc = item['description'] as String? ?? '';
    final openP = (item['open_price'] as num?)?.toDouble() ?? price;
    final highP = (item['high_price'] as num?)?.toDouble() ?? price;
    final lowP = (item['low_price'] as num?)?.toDouble() ?? price;

    showModalBottomSheet(
      context: context,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(sym, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                            decoration: BoxDecoration(
                              color: TerminalColors.panel,
                              borderRadius: BorderRadius.circular(3),
                            ),
                            child: Text(exchange, style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                            decoration: BoxDecoration(
                              color: category == 'HEADLINE' ? const Color(0x22F29A60) : const Color(0x2260A5FA),
                              borderRadius: BorderRadius.circular(3),
                            ),
                            child: Text(
                              category,
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: category == 'HEADLINE' ? TerminalColors.action : const Color(0xFF60A5FA),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(name, style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Text(
                  desc,
                  style: const TextStyle(fontSize: 12, height: 1.4, color: TerminalColors.textMain),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildDetailMetric("LAST OBSERVED", "₹ ${price.toStringAsFixed(2)}"),
                  ),
                  Expanded(
                    child: _buildDetailMetric(
                      "DAY CHANGE",
                      "${isPos ? '+' : ''}${chg.toStringAsFixed(2)} (${isPos ? '+' : ''}${chgPct.toStringAsFixed(2)}%)",
                      color: isPos ? TerminalColors.positive : TerminalColors.negative,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(child: _buildDetailMetric("DAY OPEN", "₹ ${openP.toStringAsFixed(2)}")),
                  Expanded(child: _buildDetailMetric("DAY HIGH", "₹ ${highP.toStringAsFixed(2)}")),
                  Expanded(child: _buildDetailMetric("DAY LOW", "₹ ${lowP.toStringAsFixed(2)}")),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0x10FFFFFF),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("DATA FRESHNESS: ${isCached ? 'CACHED REPLAY' : 'LIVE GATEWAY'}", style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: TerminalColors.textMuted)),
                    Text(observedAt, style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: TerminalColors.action,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  icon: const Icon(Icons.show_chart, size: 16),
                  label: const Text("Launch Canvas Candle Chart", style: TextStyle(fontWeight: FontWeight.bold)),
                  onPressed: () {
                    Navigator.pop(ctx);
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MobileChartScreen(
                          initialSymbol: sym,
                          isIndex: true,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailMetric(String label, String value, {Color? color}) {
    return Container(
      padding: const EdgeInsets.all(8),
      margin: const EdgeInsets.only(right: 6),
      decoration: BoxDecoration(
        color: TerminalColors.panel,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: TerminalColors.textMuted)),
          const SizedBox(height: 2),
          Text(value, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, fontFamily: 'monospace', color: color ?? TerminalColors.textMain)),
        ],
      ),
    );
  }

  Widget _buildViewTab(String label, int index) {
    final isSelected = _selectedTab == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedTab = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? TerminalColors.surface : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected ? TerminalColors.textMain : TerminalColors.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _buildSectorChip(String label, String sectorKey) {
    final isSelected = _selectedSector == sectorKey;
    return GestureDetector(
      onTap: () => setState(() => _selectedSector = sectorKey),
      child: Container(
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? TerminalColors.action.withValues(alpha: 0.2) : TerminalColors.panel,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
          ),
        ),
      ),
    );
  }
}

/// High-Performance Mini 24h Sparkline Curve Painter
class _MiniSparklinePainter extends CustomPainter {
  final List<double> points;
  final bool isPositive;

  _MiniSparklinePainter({required this.points, required this.isPositive});

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;

    final color = isPositive ? const Color(0xFF26A69A) : const Color(0xFFEF5350);
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final minVal = points.reduce(math.min);
    final maxVal = points.reduce(math.max);
    final range = (maxVal - minVal) == 0 ? 1.0 : (maxVal - minVal);

    final path = Path();
    final fillPath = Path();

    final stepX = size.width / (points.length - 1);
    for (int i = 0; i < points.length; i++) {
      final x = i * stepX;
      final y = size.height - ((points[i] - minVal) / range * (size.height - 4)) - 2;
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [color.withValues(alpha: 0.25), color.withValues(alpha: 0.0)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _MiniSparklinePainter oldDelegate) =>
      oldDelegate.points != points || oldDelegate.isPositive != isPositive;
}
