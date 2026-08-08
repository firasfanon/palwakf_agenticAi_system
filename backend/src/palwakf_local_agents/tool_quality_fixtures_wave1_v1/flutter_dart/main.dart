import 'package:flutter/material.dart';

class ProjectHomePage extends StatelessWidget {
  const ProjectHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Text('Projects'));
  }
}

class ReviewWorkspace extends StatefulWidget {
  const ReviewWorkspace({super.key});

  @override
  State<ReviewWorkspace> createState() => _ReviewWorkspaceState();
}

class _ReviewWorkspaceState extends State<ReviewWorkspace> {
  @override
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}
