import 'package:flutter_bloc/flutter_bloc.dart';

import '../domain/packet_configuration.dart';

class PacketCubit extends Cubit<PacketConfiguration> {
  PacketCubit() : super(PacketConfiguration.initial());
  void setTemplate(PacketTemplate template) =>
      emit(state.copyWith(template: template));
  void toggle(PacketSection section, bool selected) {
    final sections = [...state.sections];
    if (selected) {
      if (!sections.contains(section)) sections.add(section);
    } else {
      sections.remove(section);
    }
    emit(state.copyWith(sections: sections));
  }

  void move(int oldIndex, int newIndex) {
    final sections = [...state.sections];
    if (newIndex > oldIndex) newIndex--;
    final section = sections.removeAt(oldIndex);
    sections.insert(newIndex, section);
    emit(state.copyWith(sections: sections));
  }
}
