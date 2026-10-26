import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class FinExErrorBoundary extends StatefulWidget {
  final Widget child;
  final String? screenName;
  final VoidCallback? onRefresh;

  const FinExErrorBoundary({
    super.key,
    required this.child,
    this.screenName,
    this.onRefresh,
  });

  @override
  State<FinExErrorBoundary> createState() => _FinExErrorBoundaryState();
}

class _FinExErrorBoundaryState extends State<FinExErrorBoundary> {
  bool _hasError = false;
  Object? _error;
  Key _renderKey = UniqueKey();

  @override
  void didUpdateWidget(covariant FinExErrorBoundary oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_hasError) {
      setState(() {
        _hasError = false;
        _error = null;
        _renderKey = UniqueKey();
      });
    }
  }

  void _handleTryAgain() {
    setState(() {
      _hasError = false;
      _error = null;
      _renderKey = UniqueKey();
    });
  }

  void _handleRefresh() {
    setState(() {
      _hasError = false;
      _error = null;
      _renderKey = UniqueKey();
    });
    widget.onRefresh?.call();
  }

  void reportError(Object error, StackTrace? stack) {
    if (mounted) {
      setState(() {
        _hasError = true;
        _error = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_hasError) {
      return ErrorFallbackView(
        onTryAgain: _handleTryAgain,
        onRefresh: _handleRefresh,
        error: _error,
      );
    }

    return KeyedSubtree(
      key: _renderKey,
      child: _ErrorBoundaryCatcher(
        onError: (err, stack) {
          if (mounted) {
            setState(() {
              _hasError = true;
              _error = err;
            });
          }
        },
        child: widget.child,
      ),
    );
  }
}

class _ErrorBoundaryCatcher extends StatelessWidget {
  final Widget child;
  final Function(Object error, StackTrace? stack) onError;

  const _ErrorBoundaryCatcher({
    required this.child,
    required this.onError,
  });

  @override
  Widget build(BuildContext context) {
    return child;
  }
}

class ErrorFallbackView extends StatelessWidget {
  final VoidCallback onTryAgain;
  final VoidCallback onRefresh;
  final Object? error;

  const ErrorFallbackView({
    super.key,
    required this.onTryAgain,
    required this.onRefresh,
    this.error,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: TerminalColors.negativeBg,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0x40F48C7B)),
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.error_outline, size: 24, color: TerminalColors.negative),
              ),
              const SizedBox(height: 16),
              const Text(
                "Something went wrong",
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: TerminalColors.textMain,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "An unexpected runtime error occurred in this workspace view. You can try again or reload the active view.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12,
                  color: TerminalColors.textMuted,
                  height: 1.4,
                ),
              ),
              if (error != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: TerminalColors.canvas,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: Text(
                    error.toString(),
                    style: const TextStyle(
                      fontSize: 10,
                      fontFamily: 'monospace',
                      color: TerminalColors.textMuted,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: TerminalColors.action,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                      elevation: 0,
                    ),
                    onPressed: onTryAgain,
                    child: const Text("Try again", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: TerminalColors.textMain,
                      side: const BorderSide(color: TerminalColors.borderMedium),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    ),
                    onPressed: onRefresh,
                    child: const Text("Refresh", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
