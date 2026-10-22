import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';

interface MarketsScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const MarketsScreen: React.FC<MarketsScreenProps> = ({ onNavigate }) => {
  const { marketQuotes, openQuickTrade } = useFinancial();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [selectedSector, setSelectedSector] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [chartPeriod, setChartPeriod] = useState<'1D' | '1W' | '1M' | '1Y'>('1M');

  // Extended Comprehensive Indian Equities Registry (Nifty 50 / NSE Universe)
  const instruments = [
    // --- Energy, Utilities & Conglomerates ---
    {
      symbol: 'RELIANCE',
      name: 'Reliance Industries Ltd',
      sector: 'Energy & Utilities',
      price: marketQuotes['RELIANCE']?.price || 2500.0,
      changeVal: marketQuotes['RELIANCE']?.changeVal || 30.0,
      changePct: marketQuotes['RELIANCE']?.changePct || 1.21,
      isPositive: marketQuotes['RELIANCE']?.isPositive ?? true,
      open: 2475.0,
      high: marketQuotes['RELIANCE']?.high || 2515.0,
      low: marketQuotes['RELIANCE']?.low || 2468.0,
      volume: '8.4M',
      mktCap: '₹16.9T',
      sparkline: 'M0,15 L15,10 L30,16 L45,8 L60,11 L75,4',
    },
    {
      symbol: 'NTPC',
      name: 'NTPC Limited',
      sector: 'Energy & Utilities',
      price: marketQuotes['NTPC']?.price || 315.15,
      changeVal: marketQuotes['NTPC']?.changeVal || 4.2,
      changePct: marketQuotes['NTPC']?.changePct || 1.35,
      isPositive: marketQuotes['NTPC']?.isPositive ?? true,
      open: 312.0,
      high: marketQuotes['NTPC']?.high || 318.5,
      low: marketQuotes['NTPC']?.low || 311.0,
      volume: '11.2M',
      mktCap: '₹3.1T',
      sparkline: 'M0,14 L15,12 L30,8 L45,10 L60,6 L75,3',
    },
    {
      symbol: 'ONGC',
      name: 'Oil and Natural Gas Corporation',
      sector: 'Energy & Utilities',
      price: marketQuotes['ONGC']?.price || 222.0,
      changeVal: marketQuotes['ONGC']?.changeVal || 2.1,
      changePct: marketQuotes['ONGC']?.changePct || 0.95,
      isPositive: marketQuotes['ONGC']?.isPositive ?? true,
      open: 220.5,
      high: marketQuotes['ONGC']?.high || 224.0,
      low: marketQuotes['ONGC']?.low || 219.0,
      volume: '9.4M',
      mktCap: '₹2.8T',
      sparkline: 'M0,16 L15,13 L30,14 L45,9 L60,8 L75,5',
    },
    {
      symbol: 'POWERGRID',
      name: 'Power Grid Corporation of India',
      sector: 'Energy & Utilities',
      price: marketQuotes['POWERGRID']?.price || 250.45,
      changeVal: marketQuotes['POWERGRID']?.changeVal || 3.1,
      changePct: marketQuotes['POWERGRID']?.changePct || 1.25,
      isPositive: marketQuotes['POWERGRID']?.isPositive ?? true,
      open: 248.0,
      high: marketQuotes['POWERGRID']?.high || 252.5,
      low: marketQuotes['POWERGRID']?.low || 247.0,
      volume: '8.6M',
      mktCap: '₹2.3T',
      sparkline: 'M0,12 L15,10 L30,12 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'ADANIENT',
      name: 'Adani Enterprises Limited',
      sector: 'Energy & Utilities',
      price: marketQuotes['ADANIENT']?.price || 2692.0,
      changeVal: marketQuotes['ADANIENT']?.changeVal || 35.4,
      changePct: marketQuotes['ADANIENT']?.changePct || 1.33,
      isPositive: marketQuotes['ADANIENT']?.isPositive ?? true,
      open: 2660.0,
      high: marketQuotes['ADANIENT']?.high || 2715.0,
      low: marketQuotes['ADANIENT']?.low || 2650.0,
      volume: '4.8M',
      mktCap: '₹3.1T',
      sparkline: 'M0,18 L15,14 L30,11 L45,8 L60,5 L75,3',
    },

    // --- Technology & IT ---
    {
      symbol: 'TCS',
      name: 'Tata Consultancy Services',
      sector: 'Technology',
      price: marketQuotes['TCS']?.price || 3600.0,
      changeVal: marketQuotes['TCS']?.changeVal || -29.0,
      changePct: marketQuotes['TCS']?.changePct || -0.8,
      isPositive: marketQuotes['TCS']?.isPositive ?? false,
      open: 3630.0,
      high: marketQuotes['TCS']?.high || 3645.0,
      low: marketQuotes['TCS']?.low || 3590.0,
      volume: '3.1M',
      mktCap: '₹13.1T',
      sparkline: 'M0,5 L15,8 L30,6 L45,14 L60,12 L75,18',
    },
    {
      symbol: 'INFY',
      name: 'Infosys Ltd',
      sector: 'Technology',
      price: marketQuotes['INFY']?.price || 1450.0,
      changeVal: marketQuotes['INFY']?.changeVal || 7.9,
      changePct: marketQuotes['INFY']?.changePct || 0.55,
      isPositive: marketQuotes['INFY']?.isPositive ?? true,
      open: 1442.0,
      high: marketQuotes['INFY']?.high || 1458.0,
      low: marketQuotes['INFY']?.low || 1438.0,
      volume: '5.2M',
      mktCap: '₹6.0T',
      sparkline: 'M0,12 L15,14 L30,9 L45,11 L60,7 L75,5',
    },
    {
      symbol: 'WIPRO',
      name: 'Wipro Limited',
      sector: 'Technology',
      price: marketQuotes['WIPRO']?.price || 184.4,
      changeVal: marketQuotes['WIPRO']?.changeVal || 1.8,
      changePct: marketQuotes['WIPRO']?.changePct || 0.98,
      isPositive: marketQuotes['WIPRO']?.isPositive ?? true,
      open: 182.5,
      high: marketQuotes['WIPRO']?.high || 186.0,
      low: marketQuotes['WIPRO']?.low || 181.8,
      volume: '7.8M',
      mktCap: '₹2.7T',
      sparkline: 'M0,14 L15,11 L30,13 L45,9 L60,6 L75,4',
    },
    {
      symbol: 'HCLTECH',
      name: 'HCL Technologies Limited',
      sector: 'Technology',
      price: marketQuotes['HCLTECH']?.price || 1389.0,
      changeVal: marketQuotes['HCLTECH']?.changeVal || 12.5,
      changePct: marketQuotes['HCLTECH']?.changePct || 0.91,
      isPositive: marketQuotes['HCLTECH']?.isPositive ?? true,
      open: 1378.0,
      high: marketQuotes['HCLTECH']?.high || 1395.0,
      low: marketQuotes['HCLTECH']?.low || 1372.0,
      volume: '3.6M',
      mktCap: '₹3.8T',
      sparkline: 'M0,15 L15,12 L30,10 L45,8 L60,5 L75,3',
    },
    {
      symbol: 'TECHM',
      name: 'Tech Mahindra Limited',
      sector: 'Technology',
      price: marketQuotes['TECHM']?.price || 1245.0,
      changeVal: marketQuotes['TECHM']?.changeVal || -8.2,
      changePct: marketQuotes['TECHM']?.changePct || -0.65,
      isPositive: marketQuotes['TECHM']?.isPositive ?? false,
      open: 1255.0,
      high: marketQuotes['TECHM']?.high || 1260.0,
      low: marketQuotes['TECHM']?.low || 1240.0,
      volume: '2.4M',
      mktCap: '₹1.2T',
      sparkline: 'M0,6 L15,9 L30,7 L45,12 L60,14 L75,16',
    },

    // --- Banking & Financial Services ---
    {
      symbol: 'HDFCBANK',
      name: 'HDFC Bank Ltd',
      sector: 'Banking & Financials',
      price: marketQuotes['HDFCBANK']?.price || 1600.0,
      changeVal: marketQuotes['HDFCBANK']?.changeVal || 5.1,
      changePct: marketQuotes['HDFCBANK']?.changePct || 0.32,
      isPositive: marketQuotes['HDFCBANK']?.isPositive ?? true,
      open: 1595.0,
      high: marketQuotes['HDFCBANK']?.high || 1612.0,
      low: marketQuotes['HDFCBANK']?.low || 1590.0,
      volume: '9.8M',
      mktCap: '₹12.2T',
      sparkline: 'M0,14 L15,12 L30,10 L45,6 L60,8 L75,4',
    },
    {
      symbol: 'ICICIBANK',
      name: 'ICICI Bank Ltd',
      sector: 'Banking & Financials',
      price: marketQuotes['ICICIBANK']?.price || 1240.0,
      changeVal: marketQuotes['ICICIBANK']?.changeVal || 18.6,
      changePct: marketQuotes['ICICIBANK']?.changePct || 1.52,
      isPositive: marketQuotes['ICICIBANK']?.isPositive ?? true,
      open: 1225.0,
      high: marketQuotes['ICICIBANK']?.high || 1248.0,
      low: marketQuotes['ICICIBANK']?.low || 1222.0,
      volume: '11.5M',
      mktCap: '₹8.7T',
      sparkline: 'M0,16 L15,12 L30,14 L45,8 L60,6 L75,3',
    },
    {
      symbol: 'SBIN',
      name: 'State Bank of India',
      sector: 'Banking & Financials',
      price: marketQuotes['SBIN']?.price || 815.0,
      changeVal: marketQuotes['SBIN']?.changeVal || -4.2,
      changePct: marketQuotes['SBIN']?.changePct || -0.51,
      isPositive: marketQuotes['SBIN']?.isPositive ?? false,
      open: 822.0,
      high: marketQuotes['SBIN']?.high || 824.0,
      low: marketQuotes['SBIN']?.low || 811.0,
      volume: '12.8M',
      mktCap: '₹7.3T',
      sparkline: 'M0,6 L15,9 L30,7 L45,13 L60,15 L75,17',
    },
    {
      symbol: 'KOTAKBANK',
      name: 'Kotak Mahindra Bank',
      sector: 'Banking & Financials',
      price: marketQuotes['KOTAKBANK']?.price || 1780.0,
      changeVal: marketQuotes['KOTAKBANK']?.changeVal || 14.5,
      changePct: marketQuotes['KOTAKBANK']?.changePct || 0.82,
      isPositive: marketQuotes['KOTAKBANK']?.isPositive ?? true,
      open: 1768.0,
      high: marketQuotes['KOTAKBANK']?.high || 1792.0,
      low: marketQuotes['KOTAKBANK']?.low || 1765.0,
      volume: '4.2M',
      mktCap: '₹3.5T',
      sparkline: 'M0,13 L15,11 L30,12 L45,8 L60,6 L75,4',
    },
    {
      symbol: 'AXISBANK',
      name: 'Axis Bank Limited',
      sector: 'Banking & Financials',
      price: marketQuotes['AXISBANK']?.price || 1050.0,
      changeVal: marketQuotes['AXISBANK']?.changeVal || 9.2,
      changePct: marketQuotes['AXISBANK']?.changePct || 0.88,
      isPositive: marketQuotes['AXISBANK']?.isPositive ?? true,
      open: 1042.0,
      high: marketQuotes['AXISBANK']?.high || 1058.0,
      low: marketQuotes['AXISBANK']?.low || 1040.0,
      volume: '6.5M',
      mktCap: '₹3.2T',
      sparkline: 'M0,14 L15,10 L30,12 L45,7 L60,5 L75,3',
    },
    {
      symbol: 'BAJFINANCE',
      name: 'Bajaj Finance Limited',
      sector: 'Banking & Financials',
      price: marketQuotes['BAJFINANCE']?.price || 6850.0,
      changeVal: marketQuotes['BAJFINANCE']?.changeVal || 62.0,
      changePct: marketQuotes['BAJFINANCE']?.changePct || 0.91,
      isPositive: marketQuotes['BAJFINANCE']?.isPositive ?? true,
      open: 6800.0,
      high: marketQuotes['BAJFINANCE']?.high || 6890.0,
      low: marketQuotes['BAJFINANCE']?.low || 6780.0,
      volume: '1.8M',
      mktCap: '₹4.2T',
      sparkline: 'M0,15 L15,11 L30,9 L45,12 L60,7 L75,3',
    },
    {
      symbol: 'BAJAJFINSV',
      name: 'Bajaj Finserv Limited',
      sector: 'Banking & Financials',
      price: marketQuotes['BAJAJFINSV']?.price || 1580.0,
      changeVal: marketQuotes['BAJAJFINSV']?.changeVal || 11.2,
      changePct: marketQuotes['BAJAJFINSV']?.changePct || 0.71,
      isPositive: marketQuotes['BAJAJFINSV']?.isPositive ?? true,
      open: 1570.0,
      high: marketQuotes['BAJAJFINSV']?.high || 1590.0,
      low: marketQuotes['BAJAJFINSV']?.low || 1568.0,
      volume: '2.1M',
      mktCap: '₹2.5T',
      sparkline: 'M0,12 L15,10 L30,11 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'JIOFIN',
      name: 'Jio Financial Services Limited',
      sector: 'Banking & Financials',
      price: marketQuotes['JIOFIN']?.price || 320.0,
      changeVal: marketQuotes['JIOFIN']?.changeVal || 4.5,
      changePct: marketQuotes['JIOFIN']?.changePct || 1.43,
      isPositive: marketQuotes['JIOFIN']?.isPositive ?? true,
      open: 316.0,
      high: marketQuotes['JIOFIN']?.high || 324.0,
      low: marketQuotes['JIOFIN']?.low || 315.0,
      volume: '15.4M',
      mktCap: '₹2.0T',
      sparkline: 'M0,16 L15,13 L30,10 L45,8 L60,5 L75,2',
    },

    // --- Automobile ---
    {
      symbol: 'TATAMOTORS',
      name: 'Tata Motors Ltd',
      sector: 'Automobile',
      price: marketQuotes['TATAMOTORS']?.price || 924.5,
      changeVal: marketQuotes['TATAMOTORS']?.changeVal || 19.2,
      changePct: marketQuotes['TATAMOTORS']?.changePct || 2.12,
      isPositive: marketQuotes['TATAMOTORS']?.isPositive ?? true,
      open: 908.0,
      high: marketQuotes['TATAMOTORS']?.high || 932.0,
      low: marketQuotes['TATAMOTORS']?.low || 905.0,
      volume: '14.2M',
      mktCap: '₹3.4T',
      sparkline: 'M0,18 L15,14 L30,12 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'MARUTI',
      name: 'Maruti Suzuki India Limited',
      sector: 'Automobile',
      price: marketQuotes['MARUTI']?.price || 12450.0,
      changeVal: marketQuotes['MARUTI']?.changeVal || 115.0,
      changePct: marketQuotes['MARUTI']?.changePct || 0.93,
      isPositive: marketQuotes['MARUTI']?.isPositive ?? true,
      open: 12350.0,
      high: marketQuotes['MARUTI']?.high || 12520.0,
      low: marketQuotes['MARUTI']?.low || 12320.0,
      volume: '1.2M',
      mktCap: '₹3.9T',
      sparkline: 'M0,15 L15,12 L30,10 L45,8 L60,5 L75,2',
    },
    {
      symbol: 'M&M',
      name: 'Mahindra & Mahindra Limited',
      sector: 'Automobile',
      price: marketQuotes['M&M']?.price || 2840.0,
      changeVal: marketQuotes['M&M']?.changeVal || 34.0,
      changePct: marketQuotes['M&M']?.changePct || 1.21,
      isPositive: marketQuotes['M&M']?.isPositive ?? true,
      open: 2810.0,
      high: marketQuotes['M&M']?.high || 2860.0,
      low: marketQuotes['M&M']?.low || 2805.0,
      volume: '3.5M',
      mktCap: '₹3.5T',
      sparkline: 'M0,14 L15,11 L30,9 L45,6 L60,4 L75,2',
    },
    {
      symbol: 'BAJAJ-AUTO',
      name: 'Bajaj Auto Limited',
      sector: 'Automobile',
      price: marketQuotes['BAJAJ-AUTO']?.price || 9120.0,
      changeVal: marketQuotes['BAJAJ-AUTO']?.changeVal || 78.0,
      changePct: marketQuotes['BAJAJ-AUTO']?.changePct || 0.86,
      isPositive: marketQuotes['BAJAJ-AUTO']?.isPositive ?? true,
      open: 9050.0,
      high: marketQuotes['BAJAJ-AUTO']?.high || 9180.0,
      low: marketQuotes['BAJAJ-AUTO']?.low || 9020.0,
      volume: '950K',
      mktCap: '₹2.6T',
      sparkline: 'M0,13 L15,10 L30,12 L45,7 L60,5 L75,3',
    },

    // --- Consumer Goods, FMCG & Retail ---
    {
      symbol: 'ITC',
      name: 'ITC Ltd',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['ITC']?.price || 495.2,
      changeVal: marketQuotes['ITC']?.changeVal || 1.95,
      changePct: marketQuotes['ITC']?.changePct || 0.4,
      isPositive: marketQuotes['ITC']?.isPositive ?? true,
      open: 493.0,
      high: marketQuotes['ITC']?.high || 498.0,
      low: marketQuotes['ITC']?.low || 492.5,
      volume: '7.6M',
      mktCap: '₹6.2T',
      sparkline: 'M0,12 L15,11 L30,13 L45,9 L60,8 L75,6',
    },
    {
      symbol: 'HINDUNILVR',
      name: 'Hindustan Unilever Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['HINDUNILVR']?.price || 2380.0,
      changeVal: marketQuotes['HINDUNILVR']?.changeVal || 12.0,
      changePct: marketQuotes['HINDUNILVR']?.changePct || 0.51,
      isPositive: marketQuotes['HINDUNILVR']?.isPositive ?? true,
      open: 2370.0,
      high: marketQuotes['HINDUNILVR']?.high || 2395.0,
      low: marketQuotes['HINDUNILVR']?.low || 2365.0,
      volume: '2.8M',
      mktCap: '₹5.6T',
      sparkline: 'M0,11 L15,10 L30,12 L45,8 L60,7 L75,5',
    },
    {
      symbol: 'NESTLEIND',
      name: 'Nestle India Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['NESTLEIND']?.price || 2210.0,
      changeVal: marketQuotes['NESTLEIND']?.changeVal || -14.0,
      changePct: marketQuotes['NESTLEIND']?.changePct || -0.63,
      isPositive: marketQuotes['NESTLEIND']?.isPositive ?? false,
      open: 2225.0,
      high: marketQuotes['NESTLEIND']?.high || 2230.0,
      low: marketQuotes['NESTLEIND']?.low || 2200.0,
      volume: '820K',
      mktCap: '₹2.1T',
      sparkline: 'M0,5 L15,7 L30,6 L45,11 L60,13 L75,15',
    },
    {
      symbol: 'TITAN',
      name: 'Titan Company Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['TITAN']?.price || 3250.0,
      changeVal: marketQuotes['TITAN']?.changeVal || 38.0,
      changePct: marketQuotes['TITAN']?.changePct || 1.18,
      isPositive: marketQuotes['TITAN']?.isPositive ?? true,
      open: 3220.0,
      high: marketQuotes['TITAN']?.high || 3275.0,
      low: marketQuotes['TITAN']?.low || 3210.0,
      volume: '1.9M',
      mktCap: '₹2.9T',
      sparkline: 'M0,15 L15,12 L30,10 L45,7 L60,5 L75,3',
    },
    {
      symbol: 'ASIANPAINT',
      name: 'Asian Paints Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['ASIANPAINT']?.price || 2420.0,
      changeVal: marketQuotes['ASIANPAINT']?.changeVal || 16.5,
      changePct: marketQuotes['ASIANPAINT']?.changePct || 0.69,
      isPositive: marketQuotes['ASIANPAINT']?.isPositive ?? true,
      open: 2405.0,
      high: marketQuotes['ASIANPAINT']?.high || 2435.0,
      low: marketQuotes['ASIANPAINT']?.low || 2400.0,
      volume: '1.7M',
      mktCap: '₹2.3T',
      sparkline: 'M0,13 L15,11 L30,12 L45,8 L60,6 L75,4',
    },
    {
      symbol: 'TRENT',
      name: 'Trent Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['TRENT']?.price || 7150.0,
      changeVal: marketQuotes['TRENT']?.changeVal || 120.0,
      changePct: marketQuotes['TRENT']?.changePct || 1.71,
      isPositive: marketQuotes['TRENT']?.isPositive ?? true,
      open: 7050.0,
      high: marketQuotes['TRENT']?.high || 7210.0,
      low: marketQuotes['TRENT']?.low || 7030.0,
      volume: '2.5M',
      mktCap: '₹2.5T',
      sparkline: 'M0,18 L15,14 L30,11 L45,8 L60,4 L75,2',
    },
    {
      symbol: 'ZOMATO',
      name: 'Zomato Limited',
      sector: 'Consumer Goods & Retail',
      price: marketQuotes['ZOMATO']?.price || 265.0,
      changeVal: marketQuotes['ZOMATO']?.changeVal || 5.2,
      changePct: marketQuotes['ZOMATO']?.changePct || 2.0,
      isPositive: marketQuotes['ZOMATO']?.isPositive ?? true,
      open: 260.0,
      high: marketQuotes['ZOMATO']?.high || 268.0,
      low: marketQuotes['ZOMATO']?.low || 259.0,
      volume: '28.5M',
      mktCap: '₹2.3T',
      sparkline: 'M0,17 L15,13 L30,11 L45,6 L60,4 L75,2',
    },

    // --- Infrastructure, Materials & Mining ---
    {
      symbol: 'LT',
      name: 'Larsen & Toubro Limited',
      sector: 'Infrastructure & Materials',
      price: marketQuotes['LT']?.price || 3480.0,
      changeVal: marketQuotes['LT']?.changeVal || 35.0,
      changePct: marketQuotes['LT']?.changePct || 1.02,
      isPositive: marketQuotes['LT']?.isPositive ?? true,
      open: 3450.0,
      high: marketQuotes['LT']?.high || 3510.0,
      low: marketQuotes['LT']?.low || 3440.0,
      volume: '3.8M',
      mktCap: '₹4.8T',
      sparkline: 'M0,15 L15,12 L30,9 L45,7 L60,4 L75,2',
    },
    {
      symbol: 'TATASTEEL',
      name: 'Tata Steel Limited',
      sector: 'Infrastructure & Materials',
      price: marketQuotes['TATASTEEL']?.price || 148.5,
      changeVal: marketQuotes['TATASTEEL']?.changeVal || 1.8,
      changePct: marketQuotes['TATASTEEL']?.changePct || 1.23,
      isPositive: marketQuotes['TATASTEEL']?.isPositive ?? true,
      open: 147.0,
      high: marketQuotes['TATASTEEL']?.high || 150.0,
      low: marketQuotes['TATASTEEL']?.low || 146.5,
      volume: '22.4M',
      mktCap: '₹1.8T',
      sparkline: 'M0,14 L15,11 L30,13 L45,8 L60,5 L75,3',
    },
    {
      symbol: 'ULTRACEMCO',
      name: 'UltraTech Cement Limited',
      sector: 'Infrastructure & Materials',
      price: marketQuotes['ULTRACEMCO']?.price || 10950.0,
      changeVal: marketQuotes['ULTRACEMCO']?.changeVal || 95.0,
      changePct: marketQuotes['ULTRACEMCO']?.changePct || 0.88,
      isPositive: marketQuotes['ULTRACEMCO']?.isPositive ?? true,
      open: 10860.0,
      high: marketQuotes['ULTRACEMCO']?.high || 11020.0,
      low: marketQuotes['ULTRACEMCO']?.low || 10830.0,
      volume: '780K',
      mktCap: '₹3.2T',
      sparkline: 'M0,13 L15,10 L30,11 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'COALINDIA',
      name: 'Coal India Limited',
      sector: 'Infrastructure & Materials',
      price: marketQuotes['COALINDIA']?.price || 417.2,
      changeVal: marketQuotes['COALINDIA']?.changeVal || 4.8,
      changePct: marketQuotes['COALINDIA']?.changePct || 1.16,
      isPositive: marketQuotes['COALINDIA']?.isPositive ?? true,
      open: 413.0,
      high: marketQuotes['COALINDIA']?.high || 420.0,
      low: marketQuotes['COALINDIA']?.low || 411.5,
      volume: '8.2M',
      mktCap: '₹2.6T',
      sparkline: 'M0,15 L15,12 L30,10 L45,8 L60,5 L75,3',
    },
    {
      symbol: 'ADANIPORTS',
      name: 'Adani Ports & Special Economic Zone',
      sector: 'Infrastructure & Materials',
      price: marketQuotes['ADANIPORTS']?.price || 1758.8,
      changeVal: marketQuotes['ADANIPORTS']?.changeVal || 22.0,
      changePct: marketQuotes['ADANIPORTS']?.changePct || 1.27,
      isPositive: marketQuotes['ADANIPORTS']?.isPositive ?? true,
      open: 1740.0,
      high: marketQuotes['ADANIPORTS']?.high || 1775.0,
      low: marketQuotes['ADANIPORTS']?.low || 1735.0,
      volume: '5.1M',
      mktCap: '₹3.8T',
      sparkline: 'M0,16 L15,13 L30,11 L45,8 L60,5 L75,2',
    },

    // --- Healthcare & Pharmaceuticals ---
    {
      symbol: 'SUNPHARMA',
      name: 'Sun Pharmaceutical Industries',
      sector: 'Healthcare & Pharma',
      price: marketQuotes['SUNPHARMA']?.price || 1820.0,
      changeVal: marketQuotes['SUNPHARMA']?.changeVal || 15.0,
      changePct: marketQuotes['SUNPHARMA']?.changePct || 0.83,
      isPositive: marketQuotes['SUNPHARMA']?.isPositive ?? true,
      open: 1808.0,
      high: marketQuotes['SUNPHARMA']?.high || 1832.0,
      low: marketQuotes['SUNPHARMA']?.low || 1802.0,
      volume: '3.4M',
      mktCap: '₹4.4T',
      sparkline: 'M0,14 L15,11 L30,13 L45,8 L60,6 L75,3',
    },
    {
      symbol: 'DRREDDY',
      name: "Dr. Reddy's Laboratories Limited",
      sector: 'Healthcare & Pharma',
      price: marketQuotes['DRREDDY']?.price || 6350.0,
      changeVal: marketQuotes['DRREDDY']?.changeVal || -32.0,
      changePct: marketQuotes['DRREDDY']?.changePct || -0.5,
      isPositive: marketQuotes['DRREDDY']?.isPositive ?? false,
      open: 6390.0,
      high: marketQuotes['DRREDDY']?.high || 6410.0,
      low: marketQuotes['DRREDDY']?.low || 6330.0,
      volume: '920K',
      mktCap: '₹1.1T',
      sparkline: 'M0,6 L15,9 L30,7 L45,12 L60,14 L75,16',
    },

    // --- Aerospace, Defense & Telecommunications ---
    {
      symbol: 'BHARTIARTL',
      name: 'Bharti Airtel Limited',
      sector: 'Aerospace, Defense & Telecom',
      price: marketQuotes['BHARTIARTL']?.price || 1905.0,
      changeVal: marketQuotes['BHARTIARTL']?.changeVal || 24.0,
      changePct: marketQuotes['BHARTIARTL']?.changePct || 1.28,
      isPositive: marketQuotes['BHARTIARTL']?.isPositive ?? true,
      open: 1885.0,
      high: marketQuotes['BHARTIARTL']?.high || 1920.0,
      low: marketQuotes['BHARTIARTL']?.low || 1880.0,
      volume: '6.2M',
      mktCap: '₹11.2T',
      sparkline: 'M0,15 L15,11 L30,12 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'BEL',
      name: 'Bharat Electronics Limited',
      sector: 'Aerospace, Defense & Telecom',
      price: marketQuotes['BEL']?.price || 576.85,
      changeVal: marketQuotes['BEL']?.changeVal || 8.4,
      changePct: marketQuotes['BEL']?.changePct || 1.48,
      isPositive: marketQuotes['BEL']?.isPositive ?? true,
      open: 570.0,
      high: marketQuotes['BEL']?.high || 582.0,
      low: marketQuotes['BEL']?.low || 568.0,
      volume: '14.8M',
      mktCap: '₹4.2T',
      sparkline: 'M0,16 L15,12 L30,9 L45,7 L60,4 L75,2',
    },
    {
      symbol: 'HAL',
      name: 'Hindustan Aeronautics Limited',
      sector: 'Aerospace, Defense & Telecom',
      price: marketQuotes['HAL']?.price || 4989.0,
      changeVal: marketQuotes['HAL']?.changeVal || 72.0,
      changePct: marketQuotes['HAL']?.changePct || 1.46,
      isPositive: marketQuotes['HAL']?.isPositive ?? true,
      open: 4920.0,
      high: marketQuotes['HAL']?.high || 5020.0,
      low: marketQuotes['HAL']?.low || 4900.0,
      volume: '3.1M',
      mktCap: '₹3.3T',
      sparkline: 'M0,17 L15,13 L30,10 L45,7 L60,4 L75,2',
    },
  ];

  // Dynamic Sector Counts
  const sectorCounts = {
    ALL: instruments.length,
    TECH: instruments.filter((i) => i.sector.includes('Technology')).length,
    BANK: instruments.filter((i) => i.sector.includes('Banking')).length,
    ENERGY: instruments.filter((i) => i.sector.includes('Energy')).length,
    AUTO: instruments.filter((i) => i.sector.includes('Automobile')).length,
    FMCG: instruments.filter((i) => i.sector.includes('Consumer')).length,
    INFRA: instruments.filter((i) => i.sector.includes('Infrastructure')).length,
    HEALTH: instruments.filter((i) => i.sector.includes('Healthcare')).length,
    DEFENSE: instruments.filter((i) => i.sector.includes('Defense')).length,
  };

  const filtered = instruments.filter((i) => {
    const matchesSearch =
      i.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      i.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSector =
      selectedSector === 'ALL' ||
      (selectedSector === 'TECH' && i.sector.includes('Technology')) ||
      (selectedSector === 'BANK' && i.sector.includes('Banking')) ||
      (selectedSector === 'ENERGY' && i.sector.includes('Energy')) ||
      (selectedSector === 'AUTO' && i.sector.includes('Automobile')) ||
      (selectedSector === 'FMCG' && i.sector.includes('Consumer')) ||
      (selectedSector === 'INFRA' && i.sector.includes('Infrastructure')) ||
      (selectedSector === 'HEALTH' && i.sector.includes('Healthcare')) ||
      (selectedSector === 'DEFENSE' && i.sector.includes('Defense'));
    return matchesSearch && matchesSector;
  });

  // Detail View
  if (selectedSymbol) {
    const inst = instruments.find((i) => i.symbol === selectedSymbol) || instruments[0];

    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {/* Navigation Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
          <button
            onClick={() => setSelectedSymbol(null)}
            className="btn btn-secondary"
            style={{ padding: '4px 10px', fontSize: '12px' }}
          >
            ← Back to Instruments
          </button>
          <span style={{ color: 'var(--text-faint)' }}>/</span>
          <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{inst.symbol}</span>
        </div>

        {/* Header Ribbon */}
        <div className="glass-card" style={{ padding: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                {inst.name}
              </h1>
              <span className="badge badge-neutral">NSE: {inst.symbol}</span>
              <span className="badge badge-cyan">{inst.sector}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px', marginTop: '12px' }}>
              <div className="tabular-nums" style={{ fontSize: '42px', fontWeight: 800, color: '#FFFFFF' }}>
                ₹{inst.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <span className={inst.isPositive ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '14px', padding: '4px 10px' }}>
                {inst.isPositive ? '▲ +' : '▼ '}{Math.abs(inst.changeVal).toFixed(2)} ({inst.isPositive ? '+' : ''}{inst.changePct}%)
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>NSE EOD Verified Observation</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => openQuickTrade(inst.symbol)}
              className="btn-emerald"
              style={{ padding: '12px 24px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
            >
              ⚡ Instant Trade {inst.symbol}
            </button>
            <button onClick={() => onNavigate('practice')} className="btn btn-secondary">
              Open Pro Trade Desk →
            </button>
          </div>
        </div>

        {/* Chart & Fundamentals Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '28px' }}>
          {/* Main Chart */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Simulated Price History</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Historical daily candles from yfinance baseline</span>
              </div>

              {/* Timeframe Selectors */}
              <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: 'var(--radius-xs)' }}>
                {(['1D', '1W', '1M', '1Y'] as const).map((period) => (
                  <button
                    key={period}
                    onClick={() => setChartPeriod(period)}
                    style={{
                      background: chartPeriod === period ? 'var(--color-primary)' : 'transparent',
                      color: chartPeriod === period ? '#FFFFFF' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '3px',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '4px 10px',
                      cursor: 'pointer',
                    }}
                  >
                    {period}
                  </button>
                ))}
              </div>
            </div>

            {/* SVG Chart Area */}
            <div style={{ width: '100%', height: '260px' }}>
              <svg viewBox="0 0 600 200" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="marketChartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={inst.isPositive ? '#10B981' : '#EF4444'} stopOpacity="0.3" />
                    <stop offset="100%" stopColor={inst.isPositive ? '#10B981' : '#EF4444'} stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                <line x1="0" y1="40" x2="600" y2="40" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
                <line x1="0" y1="90" x2="600" y2="90" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
                <line x1="0" y1="140" x2="600" y2="140" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />

                <polygon
                  points="20,180 20,130 110,110 200,125 310,80 420,95 520,60 580,40 580,180"
                  fill="url(#marketChartGrad)"
                />
                <polyline
                  fill="none"
                  stroke={inst.isPositive ? '#10B981' : '#EF4444'}
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points="20,130 110,110 200,125 310,80 420,95 520,60 580,40"
                />
              </svg>
            </div>
          </div>

          {/* Fundamentals Sidebar */}
          <div className="glass-card" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
              Instrument Summary
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Day Range</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{inst.low} - ₹{inst.high}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Opening Price</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{inst.open}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Volume</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>{inst.volume}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Market Cap</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>{inst.mktCap}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Data Provenance</span>
                <span className="badge badge-neutral">NSE / yfinance Real Observation</span>
              </div>
            </div>

            <button
              onClick={() => openQuickTrade(inst.symbol)}
              className="btn-emerald"
              style={{ width: '100%', padding: '12px', borderRadius: 'var(--radius-sm)', marginTop: 'auto', cursor: 'pointer' }}
            >
              Place Simulated Order for {inst.symbol} →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Watchlist List View
  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', width: '100%', minWidth: 0, boxSizing: 'border-box' }}>
      {/* Search & Header */}
      <div className="markets-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap', width: '100%', minWidth: 0 }}>
        <div style={{ flex: '1 1 260px', minWidth: 0 }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Market Intelligence
          </span>
          <h1 style={{ fontSize: 'clamp(22px, 5.5vw, 36px)', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em', wordBreak: 'break-word', lineHeight: 1.2 }}>
            Instruments & Watchlist
          </h1>
          <p
            title="Verified Indian equities from NSE official reports with real live end-of-day market observations."
            style={{ color: 'var(--text-muted)', fontSize: '13.5px', marginTop: '4px', lineHeight: 1.5, wordBreak: 'break-word', whiteSpace: 'normal', overflowWrap: 'break-word', maxWidth: '100%' }}
          >
            Verified Indian equities from NSE official reports with real live end-of-day market observations.
          </p>
        </div>

        {/* Search */}
        <div className="markets-header-search" style={{ flex: '1 1 280px', maxWidth: '360px', width: '100%' }}>
          <input
            type="text"
            placeholder="Search symbol e.g., RELIANCE, TCS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '12px 16px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-medium)',
              backgroundColor: 'var(--bg-input)',
              color: '#FFFFFF',
              fontFamily: 'var(--font-sans)',
              fontSize: '14px',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      {/* Sector Filter Tabs */}
      <div className="sector-filter-scroll-row" style={{ display: 'flex', gap: '8px', overflowX: 'auto', WebkitOverflowScrolling: 'touch', width: '100%', minWidth: 0, paddingBottom: '6px' }}>
        {[
          { id: 'ALL', label: `All Sectors (${sectorCounts.ALL})` },
          { id: 'TECH', label: `Technology (${sectorCounts.TECH})` },
          { id: 'BANK', label: `Banking & Financials (${sectorCounts.BANK})` },
          { id: 'ENERGY', label: `Energy & Utilities (${sectorCounts.ENERGY})` },
          { id: 'AUTO', label: `Automobile (${sectorCounts.AUTO})` },
          { id: 'FMCG', label: `Consumer & Retail (${sectorCounts.FMCG})` },
          { id: 'INFRA', label: `Infrastructure & Materials (${sectorCounts.INFRA})` },
          { id: 'HEALTH', label: `Pharma & Healthcare (${sectorCounts.HEALTH})` },
          { id: 'DEFENSE', label: `Defense & Telecom (${sectorCounts.DEFENSE})` },
        ].map((sec) => (
          <button
            key={sec.id}
            onClick={() => setSelectedSector(sec.id)}
            className="sector-filter-pill"
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              border: selectedSector === sec.id ? '1px solid var(--color-primary)' : '1px solid var(--border-subtle)',
              background: selectedSector === sec.id ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.02)',
              color: selectedSector === sec.id ? '#FFFFFF' : 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: selectedSector === sec.id ? 600 : 500,
              cursor: 'pointer',
              flexShrink: 0,
              whiteSpace: 'nowrap',
            }}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {/* Watchlist Table */}
      <div className="glass-card" style={{ padding: '20px', width: '100%', minWidth: 0, boxSizing: 'border-box' }}>
        <div className="table-swipe-hint">← Swipe horizontally to view price, change & actions →</div>
        <div className="table-scroll-wrapper">
          <table style={{ width: '100%', minWidth: '680px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '16px' }}>Instrument</th>
                <th style={{ padding: '16px' }}>Sector</th>
                <th style={{ padding: '16px' }}>Last Price</th>
                <th style={{ padding: '16px' }}>Day Change</th>
                <th style={{ padding: '16px' }}>24h Sparkline</th>
                <th style={{ padding: '16px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inst) => (
                <tr
                  key={inst.symbol}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    transition: 'background-color var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'rgba(255, 255, 255, 0.06)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '14px',
                        }}
                      >
                        {inst.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <strong style={{ color: '#FFFFFF', fontSize: '15px' }}>{inst.symbol}</strong>
                        <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{inst.name}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '16px', color: 'var(--text-muted)' }}>{inst.sector}</td>
                  <td style={{ padding: '16px', fontWeight: 600 }} className="tabular-nums">
                    ₹{inst.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <span className={inst.isPositive ? 'badge badge-profit' : 'badge badge-loss'}>
                      {inst.isPositive ? '+' : ''}{inst.changePct}%
                    </span>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <svg width="75" height="20" style={{ overflow: 'visible' }}>
                      <path
                        d={inst.sparkline}
                        fill="none"
                        stroke={inst.isPositive ? 'var(--color-profit)' : 'var(--color-loss)'}
                        strokeWidth="2"
                      />
                    </svg>
                  </td>
                  <td style={{ padding: '16px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '8px' }}>
                      <button
                        onClick={() => setSelectedSymbol(inst.symbol)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        Inspect
                      </button>
                      <button
                        onClick={() => onNavigate('practice')}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px', color: '#38BDF8', borderColor: '#0284C7' }}
                        title="View Live TradingView Chart"
                      >
                        📈 Chart
                      </button>
                      <button
                        onClick={() => openQuickTrade(inst.symbol)}
                        className="btn-emerald"
                        style={{ padding: '6px 12px', fontSize: '12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                      >
                        Trade
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
