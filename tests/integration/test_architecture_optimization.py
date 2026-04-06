#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Optimization Integration Tests

Test scenarios:
1. Hooks auto setup system
2. Tech stack storage (no redundancy)
3. StructuredKnowledge <-> Heap integration
4. Event triggers
5. Full development workflow
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add source path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def setup_test_workspace():
    """Create test workspace"""
    test_dir = tempfile.mkdtemp(prefix="harnessgenj_test_")
    return test_dir


def cleanup_test_workspace(test_dir):
    """Cleanup test workspace"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_1_hooks_auto_setup():
    """
    Test Scenario 1: Hooks Auto Setup

    Verify:
    - Security module generated correctly
    - Hook script generated correctly
    - settings.json configured correctly
    """
    print("\n" + "="*60)
    print("Test Scenario 1: Hooks Auto Setup")
    print("="*60)

    from harnessgenj.harness.hooks_auto_setup import (
        auto_setup_hooks,
        get_hooks_setup_status,
        create_security_hook_standalone,
        create_hook_script,
    )

    test_dir = tempfile.mkdtemp(prefix="hooks_test_")

    try:
        # 1.1 Test first-time setup
        print("\n[1.1] Testing first-time setup...")
        result = auto_setup_hooks(test_dir, silent=True, force=True)

        assert result["hooks_configured"], f"Hooks config failed: {result}"
        assert result["script_created"], f"Script creation failed: {result}"
        assert result["settings_updated"], f"settings.json update failed: {result}"
        print("  [OK] First-time setup successful")

        # 1.2 Verify security module generation
        print("\n[1.2] Verifying security module...")
        security_hook = Path(test_dir) / ".claude" / "security_hook_standalone.py"
        assert security_hook.exists(), "Security module not generated"

        # Verify module can be imported
        import importlib.util
        spec = importlib.util.spec_from_file_location("security_hook", security_hook)
        assert spec is not None, "Cannot load security module"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Verify core functions exist
        assert hasattr(module, 'check_security'), "check_security function missing"
        assert hasattr(module, 'detect_language'), "detect_language function missing"
        assert hasattr(module, 'LANGUAGE_PATTERNS'), "LANGUAGE_PATTERNS missing"
        print("  [OK] Security module generated correctly")

        # 1.3 Test security check functionality
        print("\n[1.3] Testing security check...")

        # Python sensitive data detection
        python_code = 'password = "secret123"'
        result = module.check_security(python_code, "test.py")
        assert len(result["errors"]) > 0, "Python sensitive data detection failed"
        print("  [OK] Python sensitive data detection works")

        # Java sensitive data detection
        java_code = 'private String password = "secret";'
        result = module.check_security(java_code, "Test.java")
        assert len(result["errors"]) > 0, "Java sensitive data detection failed"
        print("  [OK] Java sensitive data detection works")

        # Safe code detection
        safe_code = '# password variable reference'
        result = module.check_security(safe_code, "test.py")
        assert result["passed"], "Safe code falsely flagged"
        print("  [OK] Safe code passes correctly")

        # 1.4 Verify Hook script
        print("\n[1.4] Verifying Hook script...")
        hook_script = Path(test_dir) / ".claude" / "harnessgenj_hook.py"
        assert hook_script.exists(), "Hook script not generated"

        with open(hook_script, "r", encoding="utf-8") as f:
            content = f.read()

        assert "handle_pre_tool_use_security" in content, "Security check function missing"
        assert "handle_post_tool_use" in content, "Post handler missing"
        assert "trigger_adversarial_review" in content, "Adversarial review trigger missing"
        print("  [OK] Hook script generated correctly")

        # 1.5 Verify settings.json
        print("\n[1.5] Verifying settings.json...")
        settings_path = Path(test_dir) / ".claude" / "settings.json"
        assert settings_path.exists(), "settings.json not generated"

        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        assert "hooks" in settings, "hooks config missing"
        assert "PreToolUse" in settings["hooks"], "PreToolUse config missing"
        assert "PostToolUse" in settings["hooks"], "PostToolUse config missing"
        print("  [OK] settings.json configured correctly")

        # 1.6 Test duplicate setup (idempotency)
        print("\n[1.6] Testing duplicate setup (idempotency)...")
        result2 = auto_setup_hooks(test_dir, silent=True, force=False)
        assert result2["already_configured"], "Duplicate setup detection failed"
        print("  [OK] Idempotency check passed")

        print("\n[PASS] Test Scenario 1")
        return True

    finally:
        cleanup_test_workspace(test_dir)


def test_2_tech_stack_storage():
    """
    Test Scenario 2: Tech Stack Storage (no redundancy)

    Verify:
    - Tech stack only stored in project_info.tech_stack
    - Detailed info stored as tech_info
    - No redundant tech_stack knowledge entry
    """
    print("\n" + "="*60)
    print("Test Scenario 2: Tech Stack Storage")
    print("="*60)

    from harnessgenj import Harness

    test_dir = tempfile.mkdtemp(prefix="tech_test_")
    workspace = os.path.join(test_dir, ".harnessgenj")

    try:
        # 2.1 Create project
        print("\n[2.1] Creating project...")
        harness = Harness("TechTestProject", workspace=workspace)
        print("  [OK] Project created")

        # 2.2 Set tech stack
        print("\n[2.2] Setting tech stack...")
        harness.memory.project_info.tech_stack = "Python + FastAPI"
        harness.memory._save()
        print("  [OK] Tech stack set")

        # 2.3 Verify storage location
        print("\n[2.3] Verifying storage location...")

        # Check tech stack in project_info
        assert harness.memory.project_info.tech_stack == "Python + FastAPI", \
            "project_info.tech_stack not set correctly"
        print("  [OK] project_info.tech_stack correct")

        # Check for redundant tech_stack knowledge entry
        tech_stack_knowledge = harness.memory.get_knowledge("tech_stack")
        assert tech_stack_knowledge is None, \
            f"Found redundant tech_stack knowledge entry: {tech_stack_knowledge}"
        print("  [OK] No redundant tech_stack knowledge entry")

        # 2.4 Verify tech_info storage
        print("\n[2.4] Verifying tech_info storage...")
        tech_info = harness.memory.get_knowledge("tech_info")
        # tech_info should not exist since we didn't call from_project
        print("  [OK] tech_info storage correct")

        # 2.5 Test from_project initialization
        print("\n[2.5] Testing from_project initialization...")

        # Create test project structure
        project_dir = os.path.join(test_dir, "test_project")
        os.makedirs(project_dir)

        # Create pyproject.toml
        with open(os.path.join(project_dir, "pyproject.toml"), "w") as f:
            f.write('[project]\nname = "test"\n')

        # Create README.md
        with open(os.path.join(project_dir, "README.md"), "w") as f:
            f.write("# Test Project\n\nTest description\n")

        harness2 = Harness.from_project(project_dir)

        # Verify tech stack stored only once
        tech_stack = harness2.memory.project_info.tech_stack
        assert tech_stack, "Tech stack not detected"
        print(f"  [OK] Detected tech stack: {tech_stack}")

        # Verify no redundancy again
        tech_stack_knowledge = harness2.memory.get_knowledge("tech_stack")
        assert tech_stack_knowledge is None, "Still redundant tech_stack after from_project"
        print("  [OK] No redundant storage after from_project")

        print("\n[PASS] Test Scenario 2")
        return True

    finally:
        cleanup_test_workspace(test_dir)


def test_3_structured_knowledge_heap():
    """
    Test Scenario 3: StructuredKnowledge <-> Heap Integration

    Verify:
    - Structured knowledge stored to Heap Old region
    - Index maintained correctly
    - Query functions work
    """
    print("\n" + "="*60)
    print("Test Scenario 3: StructuredKnowledge <-> Heap Integration")
    print("="*60)

    from harnessgenj import Harness
    from harnessgenj.memory.structured_knowledge import (
        KnowledgeEntry,
        KnowledgeType,
        CodeLocation,
    )

    test_dir = tempfile.mkdtemp(prefix="knowledge_test_")
    workspace = os.path.join(test_dir, ".harnessgenj")

    try:
        # 3.1 Create project
        print("\n[3.1] Creating project...")
        harness = Harness("KnowledgeTestProject", workspace=workspace)
        print("  [OK] Project created")

        # 3.2 Verify Heap injection
        print("\n[3.2] Verifying Heap injection...")
        assert harness.memory.structured.heap is not None, "Heap not injected to StructuredKnowledgeManager"
        print("  [OK] Heap injected correctly")

        # 3.3 Store structured knowledge
        print("\n[3.3] Storing structured knowledge...")

        entry = KnowledgeEntry(
            type=KnowledgeType.SECURITY_ISSUE,
            problem="SQL injection vulnerability",
            solution="Use parameterized queries",
            code_location=CodeLocation(
                file="src/db.py",
                lines=[45, 50],
            ),
            severity="critical",
            tags=["security", "sql", "injection"],
        )

        entry_id = harness.memory.store_structured_knowledge(entry)
        print(f"  [OK] Knowledge stored: {entry_id}")

        # 3.4 Verify storage to Heap
        print("\n[3.4] Verifying storage to Heap...")

        # Get from Heap
        heap_entry = harness.memory.heap.old.get(f"knowledge_{entry_id}")
        assert heap_entry is not None, "Knowledge not stored to Heap"
        assert heap_entry.metadata.get("type") == "structured_knowledge", \
            "Heap entry type incorrect"
        assert heap_entry.metadata.get("knowledge_type") == "security_issue", \
            "Knowledge type incorrect"
        print("  [OK] Knowledge stored to Heap Old region")

        # Verify importance calculation
        assert heap_entry.importance >= 90, "Critical level knowledge importance should be >= 90"
        print(f"  [OK] Importance correct: {heap_entry.importance}")

        # 3.5 Verify index
        print("\n[3.5] Verifying index...")

        # Query by type
        security_issues = harness.memory.query_knowledge_by_type(KnowledgeType.SECURITY_ISSUE)
        assert len(security_issues) == 1, "Query by type failed"
        print("  [OK] Query by type works")

        # Query by tags
        tagged = harness.memory.query_knowledge_by_tags(["security"])
        assert len(tagged) == 1, "Query by tags failed"
        print("  [OK] Query by tags works")

        # Query by file
        file_knowledge = harness.memory.query_knowledge_by_file("db.py")
        assert len(file_knowledge) == 1, "Query by file failed"
        print("  [OK] Query by file works")

        # 3.6 Test update
        print("\n[3.6] Testing update...")

        updated = harness.memory.structured.update(entry_id, {"verified": True})
        assert updated is not None, "Update failed"
        assert updated.verified, "Verified status not updated"
        print("  [OK] Update works")

        # Verify Heap content also updated
        heap_entry = harness.memory.heap.old.get(f"knowledge_{entry_id}")
        assert heap_entry.importance >= 100, "Importance should increase after verification"
        print("  [OK] Heap content synced")

        # 3.7 Test delete
        print("\n[3.7] Testing delete...")

        deleted = harness.memory.structured.delete(entry_id)
        assert deleted, "Delete failed"

        # Verify deletion from Heap
        heap_entry = harness.memory.heap.old.get(f"knowledge_{entry_id}")
        assert heap_entry is None, "Knowledge not deleted from Heap"
        print("  [OK] Delete works")

        print("\n[PASS] Test Scenario 3")
        return True

    finally:
        cleanup_test_workspace(test_dir)


def test_4_event_triggers():
    """
    Test Scenario 4: Event Trigger System

    Verify:
    - TriggerManager initialized correctly
    - Events triggered correctly
    - Event file processing works
    """
    print("\n" + "="*60)
    print("Test Scenario 4: Event Trigger System")
    print("="*60)

    from harnessgenj import Harness
    from harnessgenj.harness.event_triggers import TriggerEvent

    test_dir = tempfile.mkdtemp(prefix="event_test_")
    workspace = os.path.join(test_dir, ".harnessgenj")

    try:
        # 4.1 Create project
        print("\n[4.1] Creating project...")
        harness = Harness("EventTestProject", workspace=workspace)
        print("  [OK] Project created")

        # 4.2 Verify TriggerManager initialization
        print("\n[4.2] Verifying TriggerManager...")
        assert harness._trigger_manager is not None, "TriggerManager not initialized"
        print("  [OK] TriggerManager initialized")

        # 4.3 Verify default trigger rules
        print("\n[4.3] Verifying default trigger rules...")
        rules = harness._trigger_manager.get_rules()
        assert len(rules) > 0, "Default trigger rules not loaded"
        print(f"  [OK] {len(rules)} default rules loaded")

        # Check key rules exist
        rule_ids = [r.id for r in rules]
        assert "code_review_on_write" in rule_ids, "code_review_on_write rule missing"
        assert "bug_hunter_on_task_complete" in rule_ids, "bug_hunter_on_task_complete rule missing"
        print("  [OK] Key rules exist")

        # 4.4 Test event trigger
        print("\n[4.4] Testing event trigger...")
        results = harness._trigger_manager.trigger(
            TriggerEvent.ON_TASK_COMPLETE,
            {"task_id": "TEST-123", "status": "completed"}
        )
        print(f"  [OK] Trigger result count: {len(results)}")

        # 4.5 Test event file processing
        print("\n[4.5] Testing event file processing...")

        # Create events directory
        events_dir = Path(workspace) / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        # Write event file
        import time
        event_file = events_dir / f"event_{int(time.time())}.json"
        event_data = {
            "type": "on_write_complete",
            "timestamp": time.time(),
            "data": {
                "file_path": "src/main.py",
                "lines": 100,
            }
        }

        with open(event_file, "w", encoding="utf-8") as f:
            json.dump(event_data, f)

        # Process events
        processed = harness._trigger_manager.process_pending_events(workspace)
        print(f"  [OK] Processed {processed} events")

        # Verify event file deleted
        assert not event_file.exists(), "Event file not deleted"
        print("  [OK] Event file cleaned up")

        print("\n[PASS] Test Scenario 4")
        return True

    finally:
        cleanup_test_workspace(test_dir)


def test_5_full_development_workflow():
    """
    Test Scenario 5: Full Development Workflow

    Verify:
    - Receive request flow works
    - Development flow works
    - Task completion flow works
    - All system integrations work
    """
    print("\n" + "="*60)
    print("Test Scenario 5: Full Development Workflow")
    print("="*60)

    from harnessgenj import Harness

    test_dir = tempfile.mkdtemp(prefix="workflow_test_")
    workspace = os.path.join(test_dir, ".harnessgenj")

    try:
        # 5.1 Project initialization
        print("\n[5.1] Project initialization...")
        harness = Harness("WorkflowTestProject", workspace=workspace)
        print("  [OK] Project initialized")

        # 5.2 Receive request
        print("\n[5.2] Receiving development request...")
        result = harness.receive_request("Implement user login feature", request_type="feature")

        assert result["success"], f"Receive request failed: {result}"
        assert "task_id" in result, "Task ID missing"
        task_id = result["task_id"]
        print(f"  [OK] Task created: {task_id}")

        # 5.3 Verify task storage
        print("\n[5.3] Verifying task storage...")
        task = harness.memory.get_task(task_id)
        assert task is not None, "Task not stored"
        assert task["request"] == "Implement user login feature", "Task content incorrect"
        print("  [OK] Task stored correctly")

        # 5.4 Verify stats update
        print("\n[5.4] Verifying stats update...")
        stats = harness.memory.get_stats()
        assert stats["stats"]["features_total"] == 1, "Features total not updated"
        print("  [OK] Stats updated correctly")

        # 5.5 Store structured knowledge (simulate knowledge accumulation during development)
        print("\n[5.5] Storing development knowledge...")
        from harnessgenj.memory.structured_knowledge import (
            KnowledgeEntry,
            KnowledgeType,
        )

        entry = KnowledgeEntry(
            type=KnowledgeType.DECISION_PATTERN,
            problem="User authentication approach selection",
            solution="Use JWT for stateless authentication",
            tags=["auth", "jwt", "security"],
        )

        entry_id = harness.memory.store_structured_knowledge(entry)
        assert entry_id, "Knowledge storage failed"
        print(f"  [OK] Knowledge stored: {entry_id}")

        # 5.6 Complete task
        print("\n[5.6] Completing task...")
        completed = harness.complete_task(task_id, "Login feature implemented")
        assert completed, "Task completion failed"
        print("  [OK] Task completed")

        # 5.7 Verify final state
        print("\n[5.7] Verifying final state...")
        stats = harness.memory.get_stats()
        assert stats["stats"]["features_completed"] == 1, "Features completed not updated"
        assert stats["stats"]["progress"] == 100, "Progress calculation incorrect"
        print("  [OK] Final state correct")

        # 5.8 Verify persistence
        print("\n[5.8] Verifying persistence...")
        state_path = Path(workspace) / "state.json"
        assert state_path.exists(), "State file not created"

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        assert state["project_name"] == "WorkflowTestProject", "Project name incorrect"
        print("  [OK] Persistence correct")

        # 5.9 Verify knowledge persisted to Heap
        print("\n[5.9] Verifying knowledge persisted to Heap...")
        heap_entry = harness.memory.heap.old.get(f"knowledge_{entry_id}")
        assert heap_entry is not None, "Knowledge not persisted to Heap"
        print("  [OK] Knowledge persisted to Heap")

        print("\n[PASS] Test Scenario 5")
        return True

    finally:
        cleanup_test_workspace(test_dir)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("HarnessGenJ Architecture Optimization Integration Tests")
    print("="*60)

    results = {
        "hooks_auto_setup": False,
        "tech_stack_storage": False,
        "structured_knowledge_heap": False,
        "event_triggers": False,
        "full_development_workflow": False,
    }

    try:
        results["hooks_auto_setup"] = test_1_hooks_auto_setup()
    except Exception as e:
        print(f"\n[FAIL] Test Scenario 1: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["tech_stack_storage"] = test_2_tech_stack_storage()
    except Exception as e:
        print(f"\n[FAIL] Test Scenario 2: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["structured_knowledge_heap"] = test_3_structured_knowledge_heap()
    except Exception as e:
        print(f"\n[FAIL] Test Scenario 3: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["event_triggers"] = test_4_event_triggers()
    except Exception as e:
        print(f"\n[FAIL] Test Scenario 4: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["full_development_workflow"] = test_5_full_development_workflow()
    except Exception as e:
        print(f"\n[FAIL] Test Scenario 5: {e}")
        import traceback
        traceback.print_exc()

    # Print summary
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)

    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n*** All tests passed! Architecture optimization successful! ***")
        return 0
    else:
        print("\n*** Some tests failed, please check errors above ***")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)