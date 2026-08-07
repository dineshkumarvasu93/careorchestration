import 'package:flutter/material.dart';

import 'js_bridge.dart';
import 'models.dart';

const Color kAccent = Color(0xFF2F6E3E);
const Color kLine = Color(0xFFB8C5A4);

/// The drag-and-drop ruleset builder. This is the only thing the Flutter island
/// renders; the surrounding dashboard (form fields, publish, activate, version
/// list) is plain HTML.
class DndBuilder extends StatefulWidget {
  const DndBuilder({super.key});

  @override
  State<DndBuilder> createState() => _DndBuilderState();
}

class _DndBuilderState extends State<DndBuilder> {
  // Builder state: every module starts in the active zone.
  final List<RuleModule> _available = <RuleModule>[];
  final List<RuleModule> _active = List<RuleModule>.of(kDefaultModules);

  @override
  void initState() {
    super.initState();
    // Emit the initial state once the first frame is up so the host page knows
    // the ruleset even if the user never drags anything.
    WidgetsBinding.instance.addPostFrameCallback((_) => _emit());
  }

  void _emit() {
    final List<String> knownGapIds =
        _active.where((RuleModule m) => m.isGap).map((RuleModule m) => m.id).toList();
    final bool includeHighRisk = _active.any((RuleModule m) => m.isFlag);
    postRuleset(knownGapIds, includeHighRisk);
  }

  void _move(RuleModule module, String targetZone, {int? index}) {
    // The required "No Action" module cannot leave the active ruleset.
    if (targetZone == 'available' && module.required) {
      return;
    }
    setState(() {
      _available.removeWhere((RuleModule m) => m.id == module.id);
      _active.removeWhere((RuleModule m) => m.id == module.id);
      final List<RuleModule> target =
          targetZone == 'active' ? _active : _available;
      if (index != null && index >= 0 && index <= target.length) {
        target.insert(index, module);
      } else {
        target.add(module);
      }
    });
    _emit();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFFBFFF5),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'Drag modules between Available and Active Ruleset. '
            'Drop onto a chip to insert before it.',
            style: TextStyle(fontSize: 13, color: Color(0xFF3D543F)),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final Widget available =
                    _zone('Available Modules', 'available', _available);
                final Widget active =
                    _zone('Active Ruleset', 'active', _active);
                if (constraints.maxWidth < 520) {
                  return SingleChildScrollView(
                    child: Column(
                      children: <Widget>[
                        available,
                        const SizedBox(height: 12),
                        active,
                      ],
                    ),
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: available),
                    const SizedBox(width: 12),
                    Expanded(child: active),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _zone(String title, String zone, List<RuleModule> modules) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        DragTarget<RuleModule>(
          onWillAcceptWithDetails: (DragTargetDetails<RuleModule> d) =>
              !(zone == 'available' && d.data.required),
          onAcceptWithDetails: (DragTargetDetails<RuleModule> d) =>
              _move(d.data, zone),
          builder: (BuildContext context, List<RuleModule?> candidate,
              List<dynamic> rejected) {
            return Container(
              constraints: const BoxConstraints(minHeight: 150),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: candidate.isNotEmpty
                    ? const Color(0xFFEAF3DF)
                    : Colors.white,
                border: Border.all(
                  color: candidate.isNotEmpty ? kAccent : kLine,
                  width: 2,
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: modules.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.symmetric(vertical: 24),
                        child: Text('Drop modules here',
                            style: TextStyle(color: Color(0xFF8AA079))),
                      ),
                    )
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        for (int i = 0; i < modules.length; i++)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: _chip(modules[i], zone, i),
                          ),
                      ],
                    ),
            );
          },
        ),
      ],
    );
  }

  Widget _chip(RuleModule module, String zone, int index) {
    return DragTarget<RuleModule>(
      onWillAcceptWithDetails: (DragTargetDetails<RuleModule> d) =>
          d.data.id != module.id && !(zone == 'available' && d.data.required),
      onAcceptWithDetails: (DragTargetDetails<RuleModule> d) =>
          _move(d.data, zone, index: index),
      builder: (BuildContext context, List<RuleModule?> candidate,
          List<dynamic> rejected) {
        final Widget body = _chipBody(module);
        final Widget chip = module.required
            ? body
            : Draggable<RuleModule>(
                data: module,
                feedback: Material(
                  color: Colors.transparent,
                  child: _chipBody(module, dragging: true),
                ),
                childWhenDragging: Opacity(opacity: 0.4, child: body),
                child: body,
              );
        return Container(
          decoration: candidate.isNotEmpty
              ? const BoxDecoration(
                  border: Border(top: BorderSide(color: kAccent, width: 3)),
                )
              : null,
          child: chip,
        );
      },
    );
  }

  Widget _chipBody(RuleModule module, {bool dragging = false}) {
    final Color bg = module.isFlag ? const Color(0xFFFFF6E6) : Colors.white;
    final Color border =
        module.isFlag ? const Color(0xFFD8B877) : const Color(0xFF98AB85);
    return Container(
      width: dragging ? 240 : double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        color: module.required ? const Color(0xFFEEF5E4) : bg,
        border: Border.all(color: border),
        borderRadius: BorderRadius.circular(10),
        boxShadow: dragging
            ? const <BoxShadow>[
                BoxShadow(
                    color: Color(0x33000000),
                    blurRadius: 8,
                    offset: Offset(0, 3)),
              ]
            : null,
      ),
      child: Row(
        children: <Widget>[
          Icon(
            module.required ? Icons.lock_outline : Icons.drag_indicator,
            size: 18,
            color: const Color(0xFF8AA079),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(module.label,
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
          if (module.required)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: kAccent,
                borderRadius: BorderRadius.circular(999),
              ),
              child: const Text('required',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.bold)),
            ),
        ],
      ),
    );
  }
}
