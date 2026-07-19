import 'package:flutter/material.dart';

import '../../infrastructure/ai_backend/extraction_dto.dart';

class PdfSourceOverlay extends StatelessWidget {
  const PdfSourceOverlay({
    super.key,
    required this.source,
    required this.pageWidth,
    required this.pageHeight,
    this.highlighted = false,
  });
  final SourceBoxDto source;
  final double pageWidth;
  final double pageHeight;
  final bool highlighted;
  static Rect? transform(
    SourceBoxDto source, {
    required double pageWidth,
    required double pageHeight,
    required Size viewport,
  }) {
    if (pageWidth <= 0 ||
        pageHeight <= 0 ||
        viewport.isEmpty ||
        source.page < 1 ||
        source.x1 < 0 ||
        source.y1 < 0 ||
        source.x2 <= source.x1 ||
        source.y2 <= source.y1 ||
        source.x2 > pageWidth ||
        source.y2 > pageHeight) {
      return null;
    }
    final scaleX = viewport.width / pageWidth;
    final scaleY = viewport.height / pageHeight;
    return Rect.fromLTWH(
      source.x1 * scaleX,
      (pageHeight - source.y2) * scaleY,
      (source.x2 - source.x1) * scaleX,
      (source.y2 - source.y1) * scaleY,
    );
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final rect = transform(
        source,
        pageWidth: pageWidth,
        pageHeight: pageHeight,
        viewport: constraints.biggest,
      );
      if (rect == null) return const SizedBox.shrink();
      return Positioned.fromRect(
        rect: rect,
        child: Semantics(
          label: source.sourceDescription,
          child: IgnorePointer(
            child: DecoratedBox(
              decoration: BoxDecoration(
                border: Border.all(
                  color: highlighted ? Colors.deepPurple : Colors.teal,
                  width: highlighted ? 3 : 2,
                ),
                color: (highlighted ? Colors.deepPurple : Colors.teal)
                    .withValues(alpha: .16),
              ),
            ),
          ),
        ),
      );
    },
  );
}
