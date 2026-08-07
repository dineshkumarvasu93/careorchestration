/// A configurable rule module that can be dragged between the "Available" and
/// "Active Ruleset" zones.
///
/// - [kind] == 'gap'  -> its [id] is contributed to `known_gap_ids`.
/// - [kind] == 'flag' -> presence in the active zone sets
///   `include_high_risk_plan` to true.
class RuleModule {
  const RuleModule({
    required this.id,
    required this.label,
    required this.kind,
    this.required = false,
  });

  final String id;
  final String label;
  final String kind;
  final bool required;

  bool get isGap => kind == 'gap';
  bool get isFlag => kind == 'flag';
}

/// The default module catalog. The initial state places every module in the
/// active zone, matching the backend's baseline RULES-001 payload.
const List<RuleModule> kDefaultModules = <RuleModule>[
  RuleModule(id: 'GAP-UACR-MISSING', label: 'UACR Missing', kind: 'gap'),
  RuleModule(id: 'GAP-EGFR-DECLINE', label: 'eGFR Decline', kind: 'gap'),
  RuleModule(id: 'GAP-CKD-HIGH-RISK-PLAN', label: 'CKD High-Risk Plan', kind: 'gap'),
  RuleModule(id: 'GAP-NO-ACTION', label: 'No Action', kind: 'gap', required: true),
  RuleModule(id: 'high-risk-plan', label: 'Include High-Risk Plan', kind: 'flag'),
];
