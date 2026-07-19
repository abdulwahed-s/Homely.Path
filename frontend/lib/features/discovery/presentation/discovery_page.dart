import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../app/config/app_config.dart';
import '../../../app/theme/app_theme.dart';
import '../../../core/widgets/app_ui.dart';
import '../data/discovery_repository.dart';

class DiscoveryPage extends StatefulWidget {
  const DiscoveryPage({super.key, required this.config});
  final AppConfig config;

  @override
  State<DiscoveryPage> createState() => _DiscoveryPageState();
}

class _DiscoveryPageState extends State<DiscoveryPage> {
  final _state = TextEditingController();
  final _city = TextEditingController();
  int? _bedrooms;
  int? _householdSize;
  bool _loading = false;
  String? _error;
  DiscoveryResponse? _result;

  @override
  void dispose() {
    _state.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    if (!widget.config.hasHttpBackend) {
      setState(
        () =>
            _error = 'Property discovery requires the configured HTTP backend.',
      );
      return;
    }
    if (!RegExp(r'^[a-zA-Z]{2}$').hasMatch(_state.text.trim())) {
      setState(() => _error = 'Enter a two-letter state code, such as CA.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await DiscoveryRepository(widget.config.aiBaseUrl).search(
        state: _state.text,
        city: _city.text,
        bedrooms: _bedrooms,
        householdSize: _householdSize,
      );
      if (mounted) {
        setState(() => _result = result);
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error.toString().replaceFirst('Bad state: ', ''),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(
      locale: Localizations.localeOf(context).toLanguageTag(),
      symbol: r'$',
    );
    return Padding(
      padding: const EdgeInsets.all(28),
      child: ListView(
        children: [
          const AppSectionHeader(
            title: 'Find public housing properties',
            subtitle:
                'Search public HUD-backed property records in the places that matter to you.',
            icon: Icons.apartment_outlined,
          ),
          const AppNotice(
            child: Text(
              'Results are public records, not availability, eligibility, approval, ranking, or recommendation decisions.',
            ),
          ),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Search criteria',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Start with a state, then add optional details to narrow the list.',
                  ),
                  const SizedBox(height: 20),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      SizedBox(
                        width: 150,
                        child: TextField(
                          controller: _state,
                          textCapitalization: TextCapitalization.characters,
                          maxLength: 2,
                          buildCounter:
                              (
                                _, {
                                required currentLength,
                                required isFocused,
                                maxLength,
                              }) => null,
                          decoration: const InputDecoration(
                            labelText: 'State *',
                            hintText: 'CA',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 220,
                        child: TextField(
                          controller: _city,
                          decoration: const InputDecoration(
                            labelText: 'City (optional)',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 180,
                        child: DropdownButtonFormField<int>(
                          initialValue: _bedrooms,
                          decoration: const InputDecoration(
                            labelText: 'Bedrooms',
                          ),
                          items: [
                            for (var i = 0; i <= 4; i++)
                              DropdownMenuItem(value: i, child: Text('$i')),
                          ],
                          onChanged: (value) =>
                              setState(() => _bedrooms = value),
                        ),
                      ),
                      SizedBox(
                        width: 180,
                        child: DropdownButtonFormField<int>(
                          initialValue: _householdSize,
                          decoration: const InputDecoration(
                            labelText: 'Household size',
                          ),
                          items: [
                            for (var i = 1; i <= 8; i++)
                              DropdownMenuItem(value: i, child: Text('$i')),
                          ],
                          onChanged: (value) =>
                              setState(() => _householdSize = value),
                        ),
                      ),
                      FilledButton.icon(
                        onPressed: _loading ? null : _search,
                        icon: const Icon(Icons.search),
                        label: Text(
                          _loading ? 'Searching…' : 'Search properties',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: AppNotice(
                icon: Icons.error_outline,
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            ),
          if (_result != null) ...[
            const SizedBox(height: 28),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${_result!.resultCount} public properties found',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                const Icon(Icons.format_list_bulleted, color: appTeal),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Review each property directly with the housing provider.',
            ),
            const SizedBox(height: 12),
            for (final property in _result!.properties)
              _PropertyCard(property: property, money: money),
            const SizedBox(height: 12),
            AppNotice(child: Text(_result!.disclaimer)),
          ],
        ],
      ),
    );
  }
}

class _PropertyCard extends StatelessWidget {
  const _PropertyCard({required this.property, required this.money});
  final DiscoveryProperty property;
  final NumberFormat money;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(top: 12),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(property.name, style: Theme.of(context).textTheme.titleMedium),
          if (property.address != null || property.city != null)
            Text(
              [
                    property.address,
                    property.city,
                    property.state,
                    property.zipCode,
                  ]
                  .whereType<String>()
                  .where((value) => value.isNotEmpty)
                  .join(', '),
            ),
          const SizedBox(height: 12),
          const Chip(
            avatar: Icon(Icons.visibility_off_outlined, size: 18),
            label: Text('Availability unknown'),
          ),
          Wrap(
            spacing: 16,
            runSpacing: 8,
            children: [
              if (property.totalUnits != null)
                Text('${property.totalUnits} total units'),
              if (property.lowIncomeUnits != null)
                Text('${property.lowIncomeUnits} low-income units'),
              if (property.distanceMiles != null)
                Text('${property.distanceMiles} miles away'),
              if (property.fmrAmount != null)
                Text('HUD rent benchmark: ${money.format(property.fmrAmount)}'),
              if (property.mtspLimit != null)
                Text(
                  'HUD income reference: ${money.format(property.mtspLimit)}',
                ),
            ],
          ),
        ],
      ),
    ),
  );
}
