# -*- coding: utf-8 -*-

"""
gmncurses.controllers.milestone
~~~~~~~~~~~~~~~~~~~~~----------
"""

from concurrent.futures import wait
import functools

from gmncurses.config import ProjectMilestoneKeys
import gmncurses.data


from . import base


class ProjectMilestoneSubController(base.Controller):
    def __init__(self, view, executor, state_machine):
        self.view = view
        self.executor = executor
        self.state_machine = state_machine

    def handle(self, key):
        if key == ProjectMilestoneKeys.RELOAD:
            self.load()
        return super().handle(key)

    def load(self):
        self.state_machine.transition(self.state_machine.PROJECT_SPRINT)

        self.view.notifier.info_msg("Fetching Stats and User stories")

        res = gmncurses.data.current_sprint_id(self.view.project)

        milestone_stats_f = self.executor.milestone_stats(res, self.view.project)
        milestone_stats_f.add_done_callback(self.handle_milestone_stats)

        user_stories_f = self.executor.user_stories(res, self.view.project)
        user_stories_f.add_done_callback(self.handle_user_stories)

        milestone_tasks_f = self.executor.milestone_tasks(res, self.view.project)
        milestone_tasks_f.add_done_callback(self.handle_milestone_tasks)

        futures = (milestone_tasks_f, user_stories_f)
        futures_completed_f = self.executor.pool.submit(lambda : wait(futures, 10))
        futures_completed_f.add_done_callback(self.user_stories_info_fetched)

    def handle_milestone_stats(self, future):
        self.milestone_stats = future.result()
        if self.milestone_stats is not None:
            self.view.stats.populate(self.milestone_stats)
            self.state_machine.refresh()

    def handle_user_stories(self, future):
        self.user_stories = future.result()
        #if self.user_stories is not None:
            #self.view.user_stories_list.populate(self.user_stories)
            #self.state_machine.refresh()

    def handle_milestone_tasks(self, future):
        self.milestone_tasks = future.result()

    def user_stories_info_fetched(self, future_with_results):
        done, not_done = future_with_results.result()
        if len(done) == 2:
            self.view.user_stories_list.populate(self.user_stories, self.milestone_tasks)
            self.view.notifier.info_msg("user stories and tasks fetched")
            self.state_machine.refresh()
        else:
            # TODO retry failed operations
            self.view.notifier.error_msg("Failed to fetch milestone data")

