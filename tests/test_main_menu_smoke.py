from contextlib import ExitStack
from unittest.mock import patch


def _run_main_once(choice: str):
    import main

    with ExitStack() as stack:
        mocks = {
            "show_menu": stack.enter_context(patch("main.menu.show_menu", side_effect=[choice, "12"])),
            "console_input": stack.enter_context(patch("main.console.input", return_value="")),
            "ask_video_count": stack.enter_context(patch("main.menu.ask_video_count", return_value=1)),
            "view_content_plan": stack.enter_context(patch("main.menu.view_content_plan")),
            "main_flow": stack.enter_context(patch("main.main_flow")),
            "start_brainrot_generation": stack.enter_context(patch("main.start_brainrot_generation")),
            "start_viral_gameplay_mode": stack.enter_context(patch("main.start_viral_gameplay_mode")),
            "start_tutorial_generation": stack.enter_context(patch("main.start_tutorial_generation")),
            "start_learning_mode": stack.enter_context(patch("main.start_learning_mode")),
            "start_idea_generator": stack.enter_context(patch("main.start_idea_generator")),
            "start_rotgen_mode": stack.enter_context(patch("main.start_rotgen_mode")),
            "generate_youtube_content_package": stack.enter_context(patch("main.generate_youtube_content_package")),
            "run_video_clipper": stack.enter_context(patch("main.run_video_clipper")),
            "run_tcm_mode": stack.enter_context(patch("main.run_tcm_mode")),
        }
        main.main()
        return mocks


def test_menu_option_1_routes_to_educational():
    calls = _run_main_once("1")
    calls["ask_video_count"].assert_called_once_with("Educational", default=2)
    calls["main_flow"].assert_called_once_with(lessons_per_run=1)


def test_menu_option_2_routes_to_brainrot():
    calls = _run_main_once("2")
    calls["ask_video_count"].assert_called_once_with("Brain Rot", default=3)
    calls["start_brainrot_generation"].assert_called_once_with(1)


def test_menu_option_3_routes_to_viral():
    calls = _run_main_once("3")
    calls["start_viral_gameplay_mode"].assert_called_once_with()


def test_menu_option_4_routes_to_tutorial():
    calls = _run_main_once("4")
    calls["start_tutorial_generation"].assert_called_once_with()


def test_menu_option_5_routes_to_learning():
    calls = _run_main_once("5")
    calls["start_learning_mode"].assert_called_once_with()


def test_menu_option_6_routes_to_studio_ideas():
    calls = _run_main_once("6")
    calls["start_idea_generator"].assert_called_once_with()


def test_menu_option_7_routes_to_content_plan():
    calls = _run_main_once("7")
    calls["view_content_plan"].assert_called_once_with()


def test_menu_option_8_routes_to_rotgen():
    calls = _run_main_once("8")
    calls["ask_video_count"].assert_called_once_with("RotGen", default=3)
    calls["start_rotgen_mode"].assert_called_once_with(1)


def test_menu_option_9_routes_to_content_package():
    calls = _run_main_once("9")
    calls["generate_youtube_content_package"].assert_called_once_with()


def test_menu_option_10_routes_to_clipper():
    calls = _run_main_once("10")
    calls["run_video_clipper"].assert_called_once_with()


def test_menu_option_11_routes_to_tcm():
    calls = _run_main_once("11")
    calls["run_tcm_mode"].assert_called_once_with()


def test_menu_option_12_exits_cleanly():
    calls = _run_main_once("12")
    ignored = {"show_menu", "console_input", "view_content_plan", "ask_video_count"}
    assert all(not mock.called for name, mock in calls.items() if name not in ignored)
