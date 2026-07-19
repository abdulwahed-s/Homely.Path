import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter/services.dart';

import '../../app/theme/app_theme.dart';

class AppBrand extends StatefulWidget {
  const AppBrand({super.key, this.compact = false});
  final bool compact;

  @override
  State<AppBrand> createState() => _AppBrandState();
}

class _AppBrandState extends State<AppBrand> {
  late final Future<Uint8List?> _mark = _loadMark();

  Future<Uint8List?> _loadMark() async {
    final svg = await rootBundle.loadString('assets/images/logo.svg');
    final match = RegExp(r'base64,([^\"]+)').firstMatch(svg);
    return match == null ? null : base64Decode(match.group(1)!);
  }

  @override
  Widget build(BuildContext context) => Semantics(
    label: 'HomelyPath',
    image: true,
    child: ExcludeSemantics(
      child: SizedBox(
        width: widget.compact ? 34 : 184,
        height: 34,
        child: FutureBuilder<Uint8List?>(
          future: _mark,
          builder: (context, snapshot) => Stack(
            children: [
              if (!widget.compact)
                SvgPicture.asset(
                  'assets/images/logo_name.svg',
                  width: 184,
                  height: 34,
                ),
              if (snapshot.data case final data?)
                Image.memory(
                  data,
                  width: 34,
                  height: 34,
                  cacheWidth: 68,
                  cacheHeight: 68,
                  fit: BoxFit.fill,
                ),
            ],
          ),
        ),
      ),
    ),
  );
}

class AppFooter extends StatelessWidget {
  const AppFooter({super.key});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
    child: Text(
      'This tool did not approve, deny, score, or rank you.',
      textAlign: TextAlign.center,
      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: appInk),
    ),
  );
}

class AppContent extends StatelessWidget {
  const AppContent({super.key, required this.child, this.maxWidth = 1080});
  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxWidth),
      child: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: MediaQuery.sizeOf(context).width < 600 ? 20 : 32,
          vertical: 28,
        ),
        child: child,
      ),
    ),
  );
}

class AppSectionHeader extends StatelessWidget {
  const AppSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.icon,
  });
  final String title;
  final String? subtitle;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 22),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (icon != null) ...[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: appMint,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: appInk),
          ),
          const SizedBox(width: 14),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.headlineMedium),
              if (subtitle != null) ...[
                const SizedBox(height: 6),
                Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ],
          ),
        ),
      ],
    ),
  );
}

class AppNotice extends StatelessWidget {
  const AppNotice({
    super.key,
    required this.child,
    this.icon = Icons.info_outline,
  });
  final Widget child;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: appMint,
      borderRadius: BorderRadius.circular(9),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: appInk),
        const SizedBox(width: 10),
        Expanded(child: child),
      ],
    ),
  );
}
