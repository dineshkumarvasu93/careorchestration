import 'package:flutter/material.dart';

import 'dnd_builder.dart';

void main() {
  runApp(const RuleDndApp());
}

/// Root of the embeddable Flutter island. It renders only the drag-and-drop
/// ruleset builder; the surrounding dashboard is plain HTML and is responsible
/// for publishing, activating, and listing versions.
class RuleDndApp extends StatelessWidget {
  const RuleDndApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rule Modules',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2F6E3E)),
        scaffoldBackgroundColor: const Color(0xFFFBFFF5),
      ),
      home: const Scaffold(
        backgroundColor: Color(0xFFFBFFF5),
        body: SafeArea(child: DndBuilder()),
      ),
    );
  }
}
