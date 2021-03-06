import pytest

from zulipterminal.config.keys import keys_for_command
from zulipterminal.ui_tools.boxes import PanelSearchBox, WriteBox


BOXES = "zulipterminal.ui_tools.boxes"


class TestWriteBox:
    @pytest.fixture(autouse=True)
    def mock_external_classes(self, mocker, initial_index):
        self.view = mocker.Mock()
        self.view.model = mocker.Mock()

    @pytest.fixture()
    def write_box(self, mocker, users_fixture, user_groups_fixture,
                  streams_fixture, emojis_fixture):
        write_box = WriteBox(self.view)
        write_box.view.users = users_fixture
        write_box.model.user_group_names = [
            groups['name'] for groups in user_groups_fixture]

        write_box.view.pinned_streams = []
        write_box.view.unpinned_streams = sorted([
            [stream['name']] for stream in
            streams_fixture], key=lambda stream: stream[0].lower())

        mocker.patch('zulipterminal.ui_tools.boxes.emoji_names',
                     EMOJI_NAMES=emojis_fixture)
        return write_box

    def test_init(self, write_box):
        assert write_box.model == self.view.model
        assert write_box.view == self.view
        assert write_box.msg_edit_id is None

    @pytest.mark.parametrize('text, state', [
        ('Plain Text', 0),
        ('Plain Text', 1),
    ])
    def test_generic_autocomplete_no_prefix(self, mocker, write_box, text,
                                            state):
        return_val = write_box.generic_autocomplete(text, state)
        assert return_val == text
        write_box.view.set_typeahead_footer.assert_not_called()

    @pytest.mark.parametrize('text, state, footer_text', [
        # mentions
        ('@Human', 0, ['Human Myself', 'Human 1', 'Human 2']),
        ('@_Human', 0, ['Human Myself', 'Human 1', 'Human 2']),
        ('@Human', None, ['Human Myself', 'Human 1', 'Human 2']),
        ('@NoMatch', None, []),
        # streams
        ('#Stream', 0, ['Stream 1', 'Stream 2', 'Secret stream',
                        'Some general stream']),
        ('#Stream', None, ['Stream 1', 'Stream 2', 'Secret stream',
                           'Some general stream']),
        ('#NoMatch', None, []),
        # emojis
        (':smi', 0, ['smile', 'smiley', 'smirk']),
        (':smi', None, ['smile', 'smiley', 'smirk']),
        (':NoMatch', None, []),
    ])
    def test_generic_autocomplete_set_footer(self, mocker, write_box,
                                             state, footer_text, text):
        write_box.view.set_typeahead_footer = mocker.patch(
                                'zulipterminal.ui.View.set_typeahead_footer')
        write_box.generic_autocomplete(text, state)

        write_box.view.set_typeahead_footer.assert_called_once_with(
                                                    footer_text,
                                                    state,
                                                    False)

    @pytest.mark.parametrize('text, state, required_typeahead', [
        ('@Human', 0, '@**Human Myself**'),
        ('@Human', 1, '@**Human 1**'),
        ('@Human', 2, '@**Human 2**'),
        ('@Human', -1, '@**Human 2**'),
        ('@Human', -2, '@**Human 1**'),
        ('@Human', -3, '@**Human Myself**'),
        ('@Human', -4, None),
        ('@_Human', 0, '@_**Human Myself**'),
        ('@_Human', 1, '@_**Human 1**'),
        ('@_Human', 2, '@_**Human 2**'),
        ('@H', 1, '@**Human 1**'),
        ('@Hu', 1, '@**Human 1**'),
        ('@Hum', 1, '@**Human 1**'),
        ('@Huma', 1, '@**Human 1**'),
        ('@Human', 1, '@**Human 1**'),
        ('@Human 1', 0, '@**Human 1**'),
        ('@_H', 1, '@_**Human 1**'),
        ('@_Hu', 1, '@_**Human 1**'),
        ('@_Hum', 1, '@_**Human 1**'),
        ('@_Huma', 1, '@_**Human 1**'),
        ('@_Human', 1, '@_**Human 1**'),
        ('@_Human 1', 0, '@_**Human 1**'),
        ('@Group', 0, '@*Group 1*'),
        ('@Group', 1, '@*Group 2*'),
        ('@G', 0, '@*Group 1*'),
        ('@Gr', 0, '@*Group 1*'),
        ('@Gro', 0, '@*Group 1*'),
        ('@Grou', 0, '@*Group 1*'),
        ('@G', 1, '@*Group 2*'),
        ('@Gr', 1, '@*Group 2*'),
        ('@Gro', 1, '@*Group 2*'),
        ('@Grou', 1, '@*Group 2*'),
        # Expected sequence of autocompletes from '@'
        ('@', 0, '@*Group 1*'),
        ('@', 1, '@*Group 2*'),
        ('@', 2, '@*Group 3*'),
        ('@', 3, '@*Group 4*'),
        ('@', 4, '@**Human Myself**'),
        ('@', 5, '@**Human 1**'),
        ('@', 6, '@**Human 2**'),
        ('@', 7, None),  # Reached last match
        ('@', 8, None),  # Beyond end
        # Expected sequence of autocompletes from '@_'
        ('@_', 0, '@_**Human Myself**'),  # NOTE: No silent group mention
        ('@_', 1, '@_**Human 1**'),
        ('@_', 2, '@_**Human 2**'),
        ('@_', 3, None),  # Reached last match
        ('@_', 4, None),  # Beyond end
        ('@_', -1, '@_**Human 2**'),
    ])
    def test_generic_autocomplete_mentions(self, write_box, text,
                                           required_typeahead, state):
        typeahead_string = write_box.generic_autocomplete(text, state)
        assert typeahead_string == required_typeahead

    @pytest.mark.parametrize('text, state, required_typeahead, to_pin', [
        # With no streams pinned.
        ('#Stream', 0, '#**Stream 1**', []),  # 1st-word startswith match.
        ('#Stream', 1, '#**Stream 2**', []),  # 1st-word startswith match.
        ('#Stream', 2, '#**Secret stream**', []),  # 2nd-word startswith match.
        ('#Stream', 3, '#**Some general stream**', []),  # 3rd-word startswith.
        ('#S', 0, '#**Secret stream**', []),  # 1st-word startswith match.
        ('#S', 1, '#**Some general stream**', []),  # 1st-word startswith.
        ('#S', 2, '#**Stream 1**', []),  # 1st-word startswith match.
        ('#S', 3, '#**Stream 2**', []),  # 1st-word startswith match.
        ('#S', -1, '#**Stream 2**', []),
        ('#S', -2, '#**Stream 1**', []),
        ('#S', -3, '#**Some general stream**', []),
        ('#S', -4, '#**Secret stream**', []),
        ('#S', -5, None, []),
        ('#So', 0, '#**Some general stream**', []),
        ('#So', 1, None, []),
        ('#Se', 0, '#**Secret stream**', []),
        ('#Se', 1, None, []),
        ('#St', 0, '#**Stream 1**', []),
        ('#St', 1, '#**Stream 2**', []),
        ('#g', 0, '#**Some general stream**', []),
        ('#g', 1, None, []),
        ('#Stream 1', 0, '#**Stream 1**', []),  # Complete match.
        ('#nomatch', 0, None, []),
        ('#ene', 0, None, []),
        # With 'Secret stream' pinned.
        ('#Stream', 0, '#**Secret stream**',
         [['Secret stream'], ]),  # 2nd-word startswith match (pinned).
        ('#Stream', 1, '#**Stream 1**',
         [['Secret stream'], ]),  # 1st-word startswith match (unpinned).
        ('#Stream', 2, '#**Stream 2**',
         [['Secret stream'], ]),  # 1st-word startswith match (unpinned).
        ('#Stream', 3, '#**Some general stream**',
         [['Secret stream'], ]),  # 3rd-word starstwith match (unpinned).
        # With 'Stream 1' and 'Secret stream' pinned.
        ('#Stream', 0, '#**Stream 1**', [['Secret stream'], ['Stream 1'], ]),
        ('#Stream', 1, '#**Secret stream**', [['Secret stream'],
                                              ['Stream 1'], ]),
        ('#Stream', 2, '#**Stream 2**', [['Secret stream'], ['Stream 1'], ]),
        ('#Stream', 3, '#**Some general stream**', [['Secret stream'],
                                                    ['Stream 1'], ]),
    ])
    def test_generic_autocomplete_streams(self, write_box, text,
                                          state, required_typeahead, to_pin):
        for stream in to_pin:
            write_box.view.unpinned_streams.remove(stream)
        write_box.view.pinned_streams = to_pin
        typeahead_string = write_box.generic_autocomplete(text, state)
        assert typeahead_string == required_typeahead

    @pytest.mark.parametrize('text, state, required_typeahead', [
        (':rock_o', 0, ':rock_on:'),
        (':rock_o', 1, None),
        (':rock_o', -1, ':rock_on:'),
        (':rock_o', -2, None),
        (':smi', 0, ':smile:'),
        (':smi', 1, ':smiley:'),
        (':smi', 2, ':smirk:'),
        (':jo', 0, ':joker:'),
        (':jo', 1, ':joy_cat:'),
        (':jok', 0, ':joker:'),
        (':', 0, ':happy:'),
        (':', 1, ':joker:'),
        (':', -2, ':smiley:'),
        (':', -1, ':smirk:'),
        (':nomatch', 0, None),
        (':nomatch', -1, None),
        ])
    def test_generic_autocomplete_emojis(self, write_box, text,
                                         mocker, state, required_typeahead):
        typeahead_string = write_box.generic_autocomplete(text, state)
        assert typeahead_string == required_typeahead

    @pytest.mark.parametrize(['key', 'current_typeahead_mode',
                              'expected_typeahead_mode',
                              'expect_footer_was_reset'], [
        # footer does not reset
        (keys_for_command('AUTOCOMPLETE').pop(), False, False, False),
        (keys_for_command('AUTOCOMPLETE_REVERSE').pop(), False, False, False),
        (keys_for_command('AUTOCOMPLETE').pop(), True, True, False),
        (keys_for_command('AUTOCOMPLETE_REVERSE').pop(), True, True, False),
        # footer resets
        (keys_for_command('GO_BACK').pop(), True, False, True),
        ('space', True, False, True),
        ('k', True, False, True),
    ])
    def test_keypress_typeahead_mode_autocomplete_key(self, mocker, write_box,
                                                      current_typeahead_mode,
                                                      expected_typeahead_mode,
                                                      expect_footer_was_reset,
                                                      key):
        write_box.is_in_typeahead_mode = current_typeahead_mode
        size = (20,)

        write_box.keypress(size, key)

        assert write_box.is_in_typeahead_mode == expected_typeahead_mode
        if expect_footer_was_reset:
            self.view.set_footer_text.assert_called_once_with()
        else:
            self.view.set_footer_text.assert_not_called()


class TestPanelSearchBox:
    search_caption = "Search Results "

    @pytest.fixture
    def panel_search_box(self, mocker):
        # X is the return from keys_for_command("UNTESTED_TOKEN")
        mocker.patch(BOXES + ".keys_for_command", return_value="X")
        panel_view = mocker.Mock()
        update_func = mocker.Mock()
        return PanelSearchBox(panel_view, "UNTESTED_TOKEN", update_func)

    def test_init(self, panel_search_box):
        assert panel_search_box.search_text == "Search [X]: "
        assert panel_search_box.caption == ""
        assert panel_search_box.edit_text == panel_search_box.search_text

    def test_reset_search_text(self, panel_search_box):
        panel_search_box.set_caption(self.search_caption)
        panel_search_box.edit_text = "key words"

        panel_search_box.reset_search_text()

        assert panel_search_box.caption == ""
        assert panel_search_box.edit_text == panel_search_box.search_text

    @pytest.mark.parametrize("log, expect_body_focus_set", [
        ([], False),
        (["SOMETHING"], True)
    ])
    @pytest.mark.parametrize("enter_key", keys_for_command("ENTER"))
    def test_keypress_ENTER(self, panel_search_box,
                            enter_key, log, expect_body_focus_set):
        size = (20,)
        panel_search_box.panel_view.view.controller.is_in_editor_mode = (
            lambda: True
        )
        panel_search_box.panel_view.log = log
        panel_search_box.set_caption("")
        panel_search_box.edit_text = "key words"

        panel_search_box.keypress(size, enter_key)

        # Update this display
        # FIXME We can't test for the styled version?
        # We'd compare to [('filter_results', 'Search Results'), ' ']
        assert panel_search_box.caption == self.search_caption
        assert panel_search_box.edit_text == "key words"

        # Leave editor mode
        (panel_search_box.panel_view.view.controller.exit_editor_mode
         .assert_called_once_with())

        # Switch focus to body; if have results, move to them
        panel_search_box.panel_view.set_focus.assert_called_once_with("body")
        if expect_body_focus_set:
            (panel_search_box.panel_view.body.set_focus
             .assert_called_once_with(0))
        else:
            (panel_search_box.panel_view.body.set_focus
             .assert_not_called())

    @pytest.mark.parametrize("back_key", keys_for_command("GO_BACK"))
    def test_keypress_GO_BACK(self, panel_search_box, back_key):
        size = (20,)
        panel_search_box.panel_view.view.controller.is_in_editor_mode = (
            lambda: True
        )
        panel_search_box.set_caption(self.search_caption)
        panel_search_box.edit_text = "key words"

        panel_search_box.keypress(size, back_key)

        # Reset display
        assert panel_search_box.caption == ""
        assert panel_search_box.edit_text == panel_search_box.search_text

        # Leave editor mode
        (panel_search_box.panel_view.view.controller.exit_editor_mode
         .assert_called_once_with())

        # Switch focus to body; focus should return to previous in body
        panel_search_box.panel_view.set_focus.assert_called_once_with("body")

        # pass keypress back
        # FIXME This feels hacky to call keypress (with hardcoded 'esc' too)
        #       - should we add a second callback to update the panel?
        (panel_search_box.panel_view.keypress
         .assert_called_once_with(size, 'esc'))
