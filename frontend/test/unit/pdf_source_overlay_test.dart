import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/core/widgets/pdf_source_overlay.dart';
import 'package:homely_path/infrastructure/ai_backend/extraction_dto.dart';

void main() {
  const source = SourceBoxDto(
    page: 1,
    x1: 100,
    y1: 200,
    x2: 200,
    y2: 300,
    sourceDescription: 'source',
  );
  test(
    'converts bottom-left PDF coordinates to top-left viewport coordinates',
    () {
      final rect = PdfSourceOverlay.transform(
        source,
        pageWidth: 600,
        pageHeight: 800,
        viewport: const Size(300, 400),
      );
      expect(rect, const Rect.fromLTWH(50, 250, 50, 50));
    },
  );
  test('rejects malformed source boxes safely', () {
    const bad = SourceBoxDto(
      page: 1,
      x1: 200,
      y1: 1,
      x2: 100,
      y2: 2,
      sourceDescription: 'bad',
    );
    expect(
      PdfSourceOverlay.transform(
        bad,
        pageWidth: 600,
        pageHeight: 800,
        viewport: const Size(300, 400),
      ),
      isNull,
    );
  });
}
