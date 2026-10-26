import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class SkeletonBox extends StatefulWidget {
  final double? width;
  final double height;
  final double borderRadius;

  const SkeletonBox({
    super.key,
    this.width,
    required this.height,
    this.borderRadius = 4.0,
  });

  @override
  State<SkeletonBox> createState() => _SkeletonBoxState();
}

class _SkeletonBoxState extends State<SkeletonBox> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.35, end: 0.85).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            color: TerminalColors.panel.withValues(alpha: _animation.value),
            borderRadius: BorderRadius.circular(widget.borderRadius),
          ),
        );
      },
    );
  }
}

class SkeletonCard extends StatelessWidget {
  final double height;

  const SkeletonCard({super.key, this.height = 80});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              SkeletonBox(width: 90, height: 14),
              SkeletonBox(width: 70, height: 14),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              SkeletonBox(width: 140, height: 11),
              SkeletonBox(width: 50, height: 11),
            ],
          ),
        ],
      ),
    );
  }
}

class MarketsSkeleton extends StatelessWidget {
  const MarketsSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: 6,
      itemBuilder: (context, index) => const SkeletonCard(height: 92),
    );
  }
}

class PortfolioSkeleton extends StatelessWidget {
  const PortfolioSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: const Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  SkeletonBox(width: 120, height: 14),
                  SkeletonBox(width: 60, height: 14),
                ],
              ),
              SizedBox(height: 16),
              SkeletonBox(width: 180, height: 28),
              SizedBox(height: 16),
              SkeletonBox(width: double.infinity, height: 70, borderRadius: 6),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const SkeletonCard(height: 80),
        const SkeletonCard(height: 80),
      ],
    );
  }
}

class OverviewSkeleton extends StatelessWidget {
  const OverviewSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SkeletonBox(width: 130, height: 12),
              SizedBox(height: 8),
              SkeletonBox(width: 200, height: 22),
              SizedBox(height: 16),
              Row(
                children: [
                  Expanded(child: SkeletonBox(height: 56)),
                  SizedBox(width: 10),
                  Expanded(child: SkeletonBox(height: 56)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const SkeletonCard(height: 84),
        const SkeletonCard(height: 84),
      ],
    );
  }
}
