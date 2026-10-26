import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

enum ToastType {
  success,
  error,
  info,
}

class AppToast {
  static OverlayEntry? _currentEntry;

  static void show(
    BuildContext context,
    String message, {
    ToastType type = ToastType.info,
    String? title,
    Duration duration = const Duration(milliseconds: 3500),
  }) {
    _currentEntry?.remove();
    _currentEntry = null;

    final overlay = Overlay.of(context, rootOverlay: true);

    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (ctx) => _ToastWidget(
        message: message,
        type: type,
        title: title,
        onDismiss: () {
          if (_currentEntry == entry) {
            entry.remove();
            _currentEntry = null;
          }
        },
      ),
    );

    _currentEntry = entry;
    overlay.insert(entry);

    Future.delayed(duration, () {
      if (_currentEntry == entry) {
        entry.remove();
        _currentEntry = null;
      }
    });
  }

  static void success(BuildContext context, String message, {String? title, Duration duration = const Duration(milliseconds: 3500)}) {
    show(context, message, type: ToastType.success, title: title, duration: duration);
  }

  static void error(BuildContext context, String message, {String? title, Duration duration = const Duration(milliseconds: 4000)}) {
    show(context, message, type: ToastType.error, title: title, duration: duration);
  }

  static void info(BuildContext context, String message, {String? title, Duration duration = const Duration(milliseconds: 3500)}) {
    show(context, message, type: ToastType.info, title: title, duration: duration);
  }
}

class _ToastWidget extends StatefulWidget {
  final String message;
  final ToastType type;
  final String? title;
  final VoidCallback onDismiss;

  const _ToastWidget({
    required this.message,
    required this.type,
    this.title,
    required this.onDismiss,
  });

  @override
  State<_ToastWidget> createState() => _ToastWidgetState();
}

class _ToastWidgetState extends State<_ToastWidget> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0.0, -0.4),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _animController, curve: Curves.easeOutCubic));

    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _dismissWithAnimation() async {
    await _animController.reverse();
    widget.onDismiss();
  }

  @override
  Widget build(BuildContext context) {
    Color accentColor;
    Color bgColor;
    IconData icon;
    String defaultTitle;

    switch (widget.type) {
      case ToastType.success:
        accentColor = TerminalColors.positive;
        bgColor = const Color(0xFF14241D);
        icon = Icons.check_circle_outline;
        defaultTitle = 'Execution Success';
        break;
      case ToastType.error:
        accentColor = TerminalColors.negative;
        bgColor = const Color(0xFF2B1716);
        icon = Icons.error_outline;
        defaultTitle = 'Trade Failed';
        break;
      case ToastType.info:
        accentColor = TerminalColors.action;
        bgColor = const Color(0xFF261D15);
        icon = Icons.info_outline;
        defaultTitle = 'Notice';
        break;
    }

    final topPadding = MediaQuery.of(context).padding.top + 12;

    return Positioned(
      top: topPadding,
      left: 16,
      right: 16,
      child: Material(
        color: Colors.transparent,
        child: SlideTransition(
          position: _slideAnim,
          child: FadeTransition(
            opacity: _fadeAnim,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: accentColor.withValues(alpha: 0.5), width: 1.2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.6),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Icon(icon, size: 20, color: accentColor),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (widget.title != null || widget.type == ToastType.error)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: Text(
                              widget.title ?? defaultTitle,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: accentColor,
                                letterSpacing: 0.4,
                              ),
                            ),
                          ),
                        Text(
                          widget.message,
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            color: TerminalColors.textMain,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: _dismissWithAnimation,
                    borderRadius: BorderRadius.circular(12),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Icon(
                        Icons.close,
                        size: 16,
                        color: TerminalColors.textMuted.withValues(alpha: 0.8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
