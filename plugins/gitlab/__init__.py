from plugin import Plugin
from xml.etree import cElementTree as ET
from xml.sax.saxutils import escape
from xmpp import Resource
import json
import asyncio
import configparser
import gitlab
import slixmpp
import shlex
import re


class FakeNick(Resource):  # Only here to join for autocompletion
    def __init__(self, jid, passwd, room, nick):
        super().__init__(jid, passwd, room, nick)
        self.start()


class Gitlab(Plugin):
    INSTANCES = []

    def __init__(self, core):
        super().__init__(core)
        self.projects = {}
        self.resources = {}

        self.global_config, self.local_config = self.get_config()
        if "projects" not in self.local_config:
            self.local_config["projects"] = {}

        if "keys" not in self.global_config:
            self.global_config["keys"] = {}

        if "gitlab" not in self.global_config:
            self.global_config["gitlab"] = {"url": "", "key": "", "hook_port": 2222}

        projects = self.local_config["projects"].keys()

        self.gl = gitlab.Gitlab(self.global_config["gitlab"]["url"], self.global_config["gitlab"]["key"])
        self.gl.auth()

        for project in projects:
            self._add_project(project)

        self.register_command("add_project", self.add_project)
        self.register_command("bye", self.remove_project)
        self.register_command("list", self.list_issues)
        self.register_command("add", self.add_issue)
        self.register_command("close", self.close_issue)
        self.register_command("reopen", self.reopen_issue)
        self.register_command("assign", self.assign_issue)
        self.register_command("unassign", self.unassign_issue)
        self.register_command("comment", self.comment_issue)
        self.register_private_command("gitlab_key", self.add_key)

        def accept_client(reader, writer):
            response = ("HTTP/1.0 200 OK\r\n\r\n\r\n")
            writer.write(response.encode("utf-8"))
            writer.write_eof()
            response = yield from reader.read()
            response_http = response.decode('utf-8').split('\r\n\r\n', 1)[1]
            for self in Gitlab.INSTANCES:
                response = self.on_hook(response_http)
                if isinstance(response, tuple):
                    project, response = response
                    if project is None or response is None or project not in self.resources:
                        continue
                    self.resources[project].send_message_to_room(self.room, response)
                else:
                    for project, res in response or []:
                        if project is None or response is None or project not in self.resources:
                            continue
                        self.resources[project].send_message_to_room(self.room, res)

        if not Gitlab.INSTANCES:
            serv = asyncio.start_server(accept_client, host="127.0.0.1", port=self.global_config['gitlab']['hook_port'])
            self.serv_future = asyncio.ensure_future(serv)
        Gitlab.INSTANCES.append(self)

    def on_deletion(self):
        projects = list(self.projects.keys())
        for project in projects:
            self._remove_project(project)
        s = self.serv_future.result()
        s.close()

    def _add_project(self, project):
        if project in self.projects:
            return False

        hook_url = "http://127.0.0.1:" + self.global_config['gitlab']['hook_port']
        try:
            p = self.gl.projects.get(project)
        except:
            return False

        self.projects[project.lower()] = p
        self.resources[project] = FakeNick(
            self.core.config.bot_config['auth']['jid'],
            self.core.config.bot_config['auth']['password'],
            self.room, project.split("/", 1)[1]
        )

        for hook in p.hooks.list():
            if hook.url == hook_url:
                break
        else:
            p.hooks.create({"url": hook_url, "push_events": 1, "issues_events": 1, "job_events": 1, "note_events": 1, "merge_requests_events": 1})
        return True

    def _remove_project(self, project):
        self.resources[project].abort()
        del self.projects[project]
        del self.resources[project]

    def add_project(self, project):
        """ Usage: !add_project: namespace/project """
        if self._add_project(project):
            self.local_config['projects'][project] = ""
            self.write_local_config(self.local_config)

    def remove_project(self, project):
        """ Usage: project: !bye """
        return self.remove_project.__doc__

    def list_issues(self):
        """ Usage: project: !list """
        return self.list_issues.__doc__

    def add_issue(self, *args):
        """ Usage: project: !add title body labels """
        return self.add_issue.__doc__

    def close_issue(self, *args):
        """ Usage: project: !close issue_number """
        return self.close_issue.__doc__

    def reopen_issue(self, *args):
        """ Usage: project: !reopen issue_number """
        return self.reopen_issue.__doc__

    def assign_issue(self, *args):
        """ Usage: project: !assign issue_number """
        return self.assign_issue.__doc__

    def unassign_issue(self, *args):
        """ Usage: project: !unassign issue_number """
        return self.unassign_issue.__doc__

    def comment_issue(self, *args):
        """ Usage: project: !comment issue_number comment """
        return self.comment_issue.__doc__

    def add_key(self, key, jid):
        """ Usage: !gitlab_key your_key """
        gl = gitlab.Gitlab(self.global_config["gitlab"]["url"], key)
        try:
            gl.auth()
        except:
            return "Either your key is wrong or there is a problem with gitlab. Check your key or contact a system administrator"

        self.local_config["keys"][jid.bare] = gl.user.name
        self.write_local_config(self.local_config)

        return "The key for {} has been added to the configuration".format(gl.user.name)

    def gitlab_list(self, project):
        issues =  self.gl.project_issues.list(project_id=self.projects[project].id, state="opened")

        message = ""
        for issue in issues:
            assign = ""
            link = "https://git.bananium.fr/" + project + "/" + "issues/" + str(issue.iid)

            if issue.assignee:
                assign = "<span style='color:orange'>[{}]</span>".format(issue.assignee.name)
            message += "<span style='color:green'>#{nb}</span> - {link} - {title} {assign} \n".format(nb=issue.iid, assign=assign, link=link, title=escape(issue.title))


        if not message:
            message = "No issue found"
        return message

    def gitlab_close(self, project, iid, sudo):
        issue = self.projects[project].issues.get(iid=iid)
        issue.state_event = "close"
        issue.save(sudo=sudo)

    def gitlab_reopen(self, project, iid, sudo):
        issue = self.projects[project].issues.get(iid=iid)
        issue.state_event = "reopen"
        issue.save(sudo=sudo)

    def gitlab_assign(self, project, iid, sudo):
        issue = self.projects[project].issues.get(iid=iid)
        u = self.gl.users.list(username=sudo)[0]
        issue.save(assignee_id=u.id)

    def gitlab_unassign(self, project, iid, sudo):
        issue = self.projects[project].issues.get(iid=iid)
        issue.save(assignee_id=None)

    def gitlab_add(self, project, title, body, labels, sudo):
        self.projects[project].issues.create({'title': title, 'description': body, 'labels': labels}, sudo=sudo)

    def gitlab_comment(self, project, iid, comment, sudo):
        issue = self.projects[project].issues.get(iid=iid)
        issue.notes.create({'body': comment}, sudo=sudo)

    def gitlab_bye(self, project):
        self._remove_project(project)
        del self.local_config['projects'][project]
        self.write_local_config(self.local_config)

    def gitlab_help(self, _):
        return self.core.cmd_help()

    def execute_command(self, project, message, jid):
        try:
            command = message.split("!", 1)[1].split(" ")[0]
        except IndexError:
            for bug_number in re.findall("#(\d+)", message)[:4]:
                try:
                    issue = self.projects[project].issues.get(iid=bug_number)
                except:
                    yield "Issue not found"
                    continue

                url = escape(self.global_config["gitlab"]["url"] + project + "/issues/" + str(bug_number))
                yield f"Issue {url} – {escape(issue.title)}\n{issue.state} – {escape(issue.author.name)} – Created on: {escape(issue.created_at)}"
            return

        args = message.split("!", 1)[1][len(command):]
        args = shlex.split(args)

        if command in ["add", "close", "reopen", "assign", "unassign", "comment"]:
            if jid.bare not in self.local_config['keys']:
                yield "Unknown JID, please send a message privately to toto with !gitlab_key [your_key]"
                return
            args.append(self.local_config["keys"][jid.bare])

        func = getattr(self, "gitlab_" + command, None)
        if not func:
            yield "Unknown command"
            return

        ret = func(project, *args)

        yield ret

    def on_received_groupchat_message(self, jid, message):
        for project, resource in self.resources.copy().items():
            project_name = project.split('/', 1)[1]
            if message['body'].startswith(project_name):
                ret = self.execute_command(project, message["body"], jid)
                resource.send_message_to_room(message["from"].bare, ret)
                return

    def on_hook(self, content):
        content = json.loads(content)

        if content['object_kind'] not in ['build']:
            name = self.projects.get(content['project']['path_with_namespace'].lower(), None)
            if name is None:
                return

        if content['object_kind'] == "issue":
            return self.on_issue_hook(content)
        elif content['object_kind'] == "push":
            return self.on_push_hook(content)
        elif content['object_kind'] == "note":
            return self.on_note_hook(content)
        elif content['object_kind'] == "merge_request":
            return self.on_mr_hook(content)
        elif content['object_kind'] == "build":
            return self.on_build_hook(content)
        else:
            self.send_message_to_room("Unknown hook received" + str(content))
        return None, None

    def on_issue_hook(self, content):
        data = content['object_attributes']
        if data['action'] == "open":
            if data["created_at"] != data["updated_at"]:
                return content['project']['path_with_namespace'].lower(), "Hu"
            action = "New"
        elif data['action'] == "close":
            action = "Closed"
        elif data['action'] == "reopen":
            action = "Reopened"
        elif data['action'] == "update":
            return None, None
        else:
            action = "Unkown operation ({})".format(data['action'])

        ret = escape(
            "{action} issue #{nb}: {title} at {base_url}\n{descr}".format(
                action=action,
                title=data['title'],
                base_url=data['url'],
                nb=data['iid'],
                descr=data['description']
            )
        )
        return content['project']['path_with_namespace'].lower(), ret

    def on_push_hook(self, content):
        for commit in content['commits']:
            message = ""
            tot_minus = 0
            tot_plus = 0
            tot_files = 0
            diff = self.projects[content['project']['path_with_namespace'].lower()].commits.get(commit['id']).diff()
            for file_ in diff:
                tot_files += 1

                if file_['new_file']:
                    header = "New file | {}".format(escape(file_['new_path']))
                elif file_['renamed_file']:
                    header = "{} → {} | ".format(escape(file_['old_path']), escape(file_['new_path']))
                elif file_['deleted_file']:
                    header = "Deleted file | {}".format(escape(file_['old_path']))
                else:
                    header = "{} |".format(escape(file_['new_path']))

                plus, minus = count_diff(file_['diff'])
                tot_minus += minus
                tot_plus += plus

                nb = plus + minus
                if nb > 0:
                    plus = colorize("+" * min(plus, int((plus / nb) * 100)))
                    minus = colorize("-" * min(minus, int((minus / nb) * 100)))
                else:
                    plus = minus = ""

                message += f"{header} {nb} {plus}{minus}\n"

            message += "{nb_file} file{s} changed, ".format(nb_file=tot_files, s="s" * (tot_files > 1))
            if tot_plus:
                message += colorize("{nb_i} insertion{s}(+)".format(nb_i=tot_plus, s="s" * (tot_plus > 1)))
                if tot_minus:
                    message += ", "
            if tot_minus:
                message += colorize("{nb_d} deletion{s}(-)".format(nb_d=tot_minus, s="s" * (tot_minus > 1)))

            message = escape("New revision by {author} on branch {branch}: {url}\n{commit_message}\n".format(
                author=commit['author']['name'],
                url=commit['url'],
                branch=content['ref'].split('/', 2)[2],
                commit_message=commit['message'],
            )) + message

            yield content['project']['path_with_namespace'].lower(), message

    def on_note_hook(self, content):
        data = content['object_attributes']
        return content['project']['path_with_namespace'].lower(), "New message by {} on {}\n{}".format(content['user']['name'], data['url'], data['note'])

    def on_mr_hook(self, content):
        data = content['object_attributes']
        if data['action'] == "open":
            action = "opened"
        elif data['action'] == "close":
            action = "closed"
        elif data['action'] == "merge":
            action = "merged"
        elif data['action'] == "reopen":
            action = "reopened"
        else:
            action = "Unknown action({})".format(data['action'])

        message = "{user} {action} !{iid}: {title}\n{description}".format(
            user=content['user']['name'],
            action=action,
            iid=data['iid'],
            title=data['title'],
            description=data['description'],
        )
        return content['project']['path_with_namespace'].lower(), message

    def on_build_hook(self, content):
        message = None
        if content['build_status'] == 'success':
            message = green(escape("Build {nb} for commit {commit} passed.".format(nb=content['build_id'], commit=content['sha'])))
        elif content['build_status'] == 'failed':
            message = red(escape("Build {nb} for commit {commit}  failed.".format(nb=content['build_id'], commit=content['sha'])))
        elif content['build_status'] == 'canceled':
            message = yellow(escape("Build {nb} for commit {commit} has been canceled.".format(nb=content['build_id'], commit=content['sha'])))
        elif content['build_status'] in ['created', 'running']:
            message = ""
        project = '/'.join(part.strip().lower() for part in content['project_name'].split('/'))

        if message is None:
            return project, "Unknown build status {}".format(content['build_status'])

        return project, message


def colorize(text):
    text = re.sub(r'\++', lambda x: ("<span style='color:green'>%s</span>" % x.group(0)), text)
    text = re.sub(r'-+', lambda x: ("<span style='color:red'>%s</span>" % x.group(0)), text)
    return text

def green(text):
    text = "<span style='color:green'>%s</span>" % text
    return text


def red(text):
    text = "<span style='color:red'>%s</span>" % text
    return text


def yellow(text):
    text = "<span style='color:yellow'>%s</span>" % text
    return text

ADDEDLINE = """\+(?![+])(.*)"""
REMOVEDLINE = """-(?![-])(.*)"""


def count_diff(diff):
    plus = 0
    minus = 0
    for line in diff.split('\n'):
        if re.match(ADDEDLINE, line):
            plus += 1
        elif re.match(REMOVEDLINE, line):
            minus += 1
    return plus, minus

