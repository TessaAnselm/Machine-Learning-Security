from streamlit.testing.v1 import AppTest


def test_monster_missions_and_settings_reset():
    app = AppTest.from_file('../app.py', default_timeout=60).run()
    assert not app.exception
    assert app.session_state.completed_missions == []
    app.button[0].click().run()
    assert app.session_state.completed_missions == [0]
    next(button for button in app.button if button.label.startswith('Next mission')).click().run()
    assert app.session_state.mission.startswith('2')
    next(button for button in app.button if button.label == 'Choose my detector').click().run()
    assert app.session_state.completed_missions == [0, 1]
    next(button for button in app.button if button.label.startswith('Next mission')).click().run()
    app.radio(key='mistake_answer').set_value('A false alarm').run()
    app.button[0].click().run()
    assert app.session_state.completed_missions == [0, 1]
    app.radio(key='mistake_answer').set_value('A missed attack').run()
    app.button[0].click().run()
    assert app.session_state.completed_missions == [0, 1, 2]
    assert any('All three missions complete' in item.value for item in app.success)
    app.checkbox[0].uncheck().run()
    assert not app.exception
    app.slider[1].set_value(10).run(timeout=60)
    assert app.session_state.completed_missions == []
    assert not app.exception
