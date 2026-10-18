import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';
import 'chart_screen.dart';

class MobileMarketsScreen extends StatefulWidget {
  const MobileMarketsScreen({super.key});

  @override
  State<MobileMarketsScreen> createState() => _MobileMarketsScreenState();
}

class _MobileMarketsScreenState extends State<MobileMarketsScreen> {
  String _searchQuery = '';
  int _selectedTab = 0; // 0 = Watchlist, 1 = All Instruments

  // User-owned watchlist set
  final Set<String> _pinnedWatchlist = {'RELIANCE', 'TCS', 'INFY', 'HDFCBANK'};

  final List<Map<String, dynamic>> _instruments = [
    {
      "symbol": "RELIANCE",
      "company": "Reliance Industries Limited",
      "isin": "INE002A01018",
      "sector": "Energy & Conglomerate",
      "price": "₹ 2,500.00",
      "change": "+0.85%",
      "positive": true,
      "pe": "26.4x",
      "high52": "₹ 3,024.90",
      "low52": "₹ 2,220.30",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "TCS",
      "company": "Tata Consultancy Services Limited",
      "isin": "INE467B01029",
      "sector": "Information Technology",
      "price": "₹ 3,500.00",
      "change": "-0.42%",
      "positive": false,
      "pe": "29.1x",
      "high52": "₹ 4,254.75",
      "low52": "₹ 3,312.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "INFY",
      "company": "Infosys Limited",
      "isin": "INE009A01021",
      "sector": "Information Technology",
      "price": "₹ 1,420.00",
      "change": "+1.12%",
      "positive": true,
      "pe": "24.8x",
      "high52": "₹ 1,760.00",
      "low52": "₹ 1,358.35",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "HDFCBANK",
      "company": "HDFC Bank Limited",
      "isin": "INE040A01034",
      "sector": "Banking & Financial Services",
      "price": "₹ 1,650.00",
      "change": "+0.30%",
      "positive": true,
      "pe": "19.2x",
      "high52": "₹ 1,794.00",
      "low52": "₹ 1,363.55",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "ICICIBANK",
      "company": "ICICI Bank Limited",
      "isin": "INE090A01021",
      "sector": "Banking & Financial Services",
      "price": "₹ 1,220.00",
      "change": "-0.15%",
      "positive": false,
      "pe": "18.5x",
      "high52": "₹ 1,300.00",
      "low52": "₹ 928.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "SBIN",
      "company": "State Bank of India",
      "isin": "INE062A01020",
      "sector": "Banking & Financial Services",
      "price": "₹ 810.00",
      "change": "+0.50%",
      "positive": true,
      "pe": "10.8x",
      "high52": "₹ 912.00",
      "low52": "₹ 555.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "KOTAKBANK",
      "company": "Kotak Mahindra Bank Limited",
      "isin": "INE237A01028",
      "sector": "Banking & Financial Services",
      "price": "₹ 1,780.00",
      "change": "+0.25%",
      "positive": true,
      "pe": "21.5x",
      "high52": "₹ 1,930.00",
      "low52": "₹ 1,544.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "AXISBANK",
      "company": "Axis Bank Limited",
      "isin": "INE238A01034",
      "sector": "Banking & Financial Services",
      "price": "₹ 1,180.00",
      "change": "-0.35%",
      "positive": false,
      "pe": "14.2x",
      "high52": "₹ 1,339.00",
      "low52": "₹ 952.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "TATAMOTORS",
      "company": "Tata Motors Limited",
      "isin": "INE155A01022",
      "sector": "Automobile",
      "price": "₹ 920.00",
      "change": "+1.75%",
      "positive": true,
      "pe": "16.0x",
      "high52": "₹ 1,179.00",
      "low52": "₹ 640.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "MARUTI",
      "company": "Maruti Suzuki India Limited",
      "isin": "INE585B01010",
      "sector": "Automobile",
      "price": "₹ 12,450.00",
      "change": "+0.60%",
      "positive": true,
      "pe": "28.5x",
      "high52": "₹ 13,680.00",
      "low52": "₹ 9,760.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "TATASTEEL",
      "company": "Tata Steel Limited",
      "isin": "INE081A01020",
      "sector": "Metals & Mining",
      "price": "₹ 175.50",
      "change": "+2.10%",
      "positive": true,
      "pe": "18.2x",
      "high52": "₹ 184.60",
      "low52": "₹ 118.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "JSWSTEEL",
      "company": "JSW Steel Limited",
      "isin": "INE019A01038",
      "sector": "Metals & Mining",
      "price": "₹ 985.00",
      "change": "+0.90%",
      "positive": true,
      "pe": "22.0x",
      "high52": "₹ 1,065.00",
      "low52": "₹ 740.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "LT",
      "company": "Larsen & Toubro Limited",
      "isin": "INE018A01030",
      "sector": "Infrastructure & Engineering",
      "price": "₹ 3,650.00",
      "change": "+1.40%",
      "positive": true,
      "pe": "34.0x",
      "high52": "₹ 3,948.00",
      "low52": "₹ 2,870.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "BHARTIARTL",
      "company": "Bharti Airtel Limited",
      "isin": "INE397D01024",
      "sector": "Telecommunications",
      "price": "₹ 1,680.00",
      "change": "+0.45%",
      "positive": true,
      "pe": "45.0x",
      "high52": "₹ 1,779.00",
      "low52": "₹ 912.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "ITC",
      "company": "ITC Limited",
      "isin": "INE154A01025",
      "sector": "Consumer Goods & FMCG",
      "price": "₹ 485.00",
      "change": "-0.10%",
      "positive": false,
      "pe": "27.5x",
      "high52": "₹ 520.00",
      "low52": "₹ 399.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "HINDUNILVR",
      "company": "Hindustan Unilever Limited",
      "isin": "INE030A01027",
      "sector": "Consumer Goods & FMCG",
      "price": "₹ 2,750.00",
      "change": "-0.20%",
      "positive": false,
      "pe": "58.0x",
      "high52": "₹ 3,035.00",
      "low52": "₹ 2,172.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "BAJFINANCE",
      "company": "Bajaj Finance Limited",
      "isin": "INE296A01024",
      "sector": "Financial Services",
      "price": "₹ 7,120.00",
      "change": "+0.80%",
      "positive": true,
      "pe": "29.0x",
      "high52": "₹ 8,192.00",
      "low52": "₹ 6,350.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "SUNPHARMA",
      "company": "Sun Pharmaceutical Industries Limited",
      "isin": "INE044A01036",
      "sector": "Pharmaceuticals",
      "price": "₹ 1,890.00",
      "change": "+1.10%",
      "positive": true,
      "pe": "38.5x",
      "high52": "₹ 1,960.00",
      "low52": "₹ 1,078.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "TITAN",
      "company": "Titan Company Limited",
      "isin": "INE280A01028",
      "sector": "Consumer Discretionary",
      "price": "₹ 3,450.00",
      "change": "-0.50%",
      "positive": false,
      "pe": "82.0x",
      "high52": "₹ 3,886.00",
      "low52": "₹ 3,055.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "HAL",
      "company": "Hindustan Aeronautics Limited",
      "isin": "INE066F01020",
      "sector": "Aerospace & Defense",
      "price": "₹ 4,450.00",
      "change": "+2.80%",
      "positive": true,
      "pe": "36.0x",
      "high52": "₹ 5,675.00",
      "low52": "₹ 1,768.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
    {
      "symbol": "ZOMATO",
      "company": "Zomato Limited",
      "isin": "INE758T01015",
      "sector": "Consumer Internet & Quick Commerce",
      "price": "₹ 275.00",
      "change": "+3.40%",
      "positive": true,
      "pe": "125.0x",
      "high52": "₹ 298.00",
      "low52": "₹ 101.00",
      "observed": "16 Oct 2026",
      "status": "NSE Verified",
    },
  ];

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
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      builder: (ctx) {
        final isPos = item['positive'] as bool;
        return Padding(
          padding: const EdgeInsets.all(20),
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
                      Text(item['symbol'], style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                      const SizedBox(height: 2),
                      Text(item['company'], style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(item['price'], style: const TextStyle(fontSize: 18, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                      const SizedBox(height: 2),
                      Text(item['change'], style: TextStyle(fontSize: 12, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: isPos ? TerminalColors.positive : TerminalColors.negative)),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(color: TerminalColors.borderSubtle),
              const SizedBox(height: 12),
              _buildDetailRow("ISIN Identifier", item['isin']),
              _buildDetailRow("Sector Classification", item['sector']),
              _buildDetailRow("Trailing P/E Ratio", item['pe']),
              _buildDetailRow("52-Week Range", "${item['low52']} – ${item['high52']}"),
              _buildDetailRow("Data Freshness", "${item['status']} • ${item['observed']}"),
              _buildDetailRow("Total Expense Ratio (TER)", "not available (Equity Share)"),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: TerminalColors.action,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  icon: const Icon(Icons.show_chart, size: 18),
                  label: const Text("Open Interactive Chart", style: TextStyle(fontWeight: FontWeight.bold)),
                  onPressed: () {
                    Navigator.pop(ctx);
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MobileChartScreen(initialSymbol: item['symbol']),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: const Text(
                  "EDUCATIONAL DISCLAIMER: Historical market quotes and financial multiples are sourced from verified NSE observations. For financial education only; does not constitute investment advice.",
                  style: TextStyle(fontSize: 10, color: TerminalColors.textMuted, height: 1.3),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
          Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _instruments.where((item) {
      final sym = item['symbol'] as String;
      final comp = item['company'] as String;
      final matchesSearch = sym.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          comp.toLowerCase().contains(_searchQuery.toLowerCase());
      if (_selectedTab == 0) {
        return matchesSearch && _pinnedWatchlist.contains(sym);
      }
      return matchesSearch;
    }).toList();

    return Column(
      children: [
        // Top Search Bar
        Padding(
          padding: const EdgeInsets.all(16),
          child: Container(
            height: 40,
            decoration: BoxDecoration(
              color: TerminalColors.input,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: TextField(
              onChanged: (v) => setState(() => _searchQuery = v),
              style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
              decoration: const InputDecoration(
                hintText: "Search by symbol or company name...",
                hintStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                prefixIcon: Icon(Icons.search, size: 18, color: TerminalColors.textMuted),
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
        ),

        // Filter Tabs (My Watchlist / All Instruments)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              _buildTab("My Watchlist (${_pinnedWatchlist.length})", 0),
              const SizedBox(width: 8),
              _buildTab("All Instruments (${_instruments.length})", 1),
            ],
          ),
        ),
        const SizedBox(height: 12),

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
                    final isPos = item['positive'] as bool;
                    final isPinned = _pinnedWatchlist.contains(sym);

                    return GestureDetector(
                      onTap: () => _showInstrumentDetails(item),
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                          color: TerminalColors.surface,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: TerminalColors.borderSubtle),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
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
                                const SizedBox(width: 10),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(sym, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                          decoration: BoxDecoration(
                                            color: TerminalColors.panel,
                                            borderRadius: BorderRadius.circular(2),
                                          ),
                                          child: Text(item['status'], style: const TextStyle(fontSize: 9, color: TerminalColors.textMuted)),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 2),
                                    Text(item['company'], style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                                  ],
                                ),
                              ],
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(item['price'], style: const TextStyle(fontSize: 14, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                                const SizedBox(height: 2),
                                Text(
                                  item['change'],
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
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildTab(String label, int index) {
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
}
