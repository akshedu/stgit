
__copyright__ = """
Copyright (C) 2005, Catalin Marinas <catalin.marinas@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import sys, os
from optparse import OptionParser, make_option

from stgit.commands.common import *
from stgit.utils import *
from stgit import stack, git
from stgit.config import config


help = 'generate a new commit for the current patch'
usage = """%prog [options] [<files...>]

Include the latest tree changes in the current patch. This command
generates a new GIT commit object with the patch details, the previous
one no longer being visible. The patch attributes like author,
committer and description can be changed with the command line
options. The '--force' option is useful when a commit object was
created with a different tool but the changes need to be included in
the current patch."""

options = [make_option('-f', '--force',
                       help = 'force the refresh even if HEAD and '\
                       'top differ',
                       action = 'store_true'),
           make_option('-e', '--edit',
                       help = 'invoke an editor for the patch '\
                       'description',
                       action = 'store_true'),
           make_option('-s', '--showpatch',
                       help = 'show the patch content in the editor buffer',
                       action = 'store_true'),
           make_option('--update',
                       help = 'only update the current patch files',
                       action = 'store_true'),
           make_option('--undo',
                       help = 'revert the commit generated by the last refresh',
                       action = 'store_true'),
           make_option('-m', '--message',
                       help = 'use MESSAGE as the patch ' \
                       'description'),
           make_option('-a', '--annotate', metavar = 'NOTE',
                       help = 'annotate the patch log entry'),
           make_option('--author', metavar = '"NAME <EMAIL>"',
                       help = 'use "NAME <EMAIL>" as the author details'),
           make_option('--authname',
                       help = 'use AUTHNAME as the author name'),
           make_option('--authemail',
                       help = 'use AUTHEMAIL as the author e-mail'),
           make_option('--authdate',
                       help = 'use AUTHDATE as the author date'),
           make_option('--commname',
                       help = 'use COMMNAME as the committer name'),
           make_option('--commemail',
                       help = 'use COMMEMAIL as the committer ' \
                       'e-mail'),
           make_option('-p', '--patch',
                       help = 'refresh (applied) PATCH instead of the top one'),
           make_option('--sign',
                       help = 'add Signed-off-by line',
                       action = 'store_true'),
           make_option('--ack',
                       help = 'add Acked-by line',
                       action = 'store_true')]


def func(parser, options, args):
    autoresolved = config.get('stgit.autoresolved')

    if autoresolved != 'yes':
        check_conflicts()

    if options.patch:
        if args or options.update:
            raise CmdException, \
                  'Only full refresh is available with the --patch option'
        patch = options.patch
        if not crt_series.patch_applied(patch):
            raise CmdException, 'Patches "%s" not applied' % patch
    else:
        patch = crt_series.get_current()
        if not patch:
            raise CmdException, 'No patches applied'

    if not options.force:
        check_head_top_equal()

    if options.undo:
        out.start('Undoing the refresh of "%s"' % patch)
        crt_series.undo_refresh()
        out.done()
        return

    if options.author:
        options.authname, options.authemail = name_email(options.author)

    if options.sign:
        sign_str = 'Signed-off-by'
        if options.ack:
            raise CmdException, '--ack and --sign were both specified'
    elif options.ack:
        sign_str = 'Acked-by'
    else:
        sign_str = None

    files = [x[1] for x in git.tree_status(verbose = True)]
    if args:
        files = [f for f in files if f in args]

    if files or not crt_series.head_top_equal() \
           or options.edit or options.message \
           or options.authname or options.authemail or options.authdate \
           or options.commname or options.commemail \
           or options.sign or options.ack:

        if options.patch:
            applied = crt_series.get_applied()
            between = applied[:applied.index(patch):-1]
            pop_patches(between, keep = True)
        elif options.update:
            rev1 = git_id('//bottom')
            rev2 = git_id('//top')
            patch_files = git.barefiles(rev1, rev2).split('\n')
            files = [f for f in files if f in patch_files]
            if not files:
                out.info('No modified files for updating patch "%s"' % patch)
                return

        out.start('Refreshing patch "%s"' % patch)

        if autoresolved == 'yes':
            resolved_all()
        crt_series.refresh_patch(files = files,
                                 message = options.message,
                                 edit = options.edit,
                                 show_patch = options.showpatch,
                                 author_name = options.authname,
                                 author_email = options.authemail,
                                 author_date = options.authdate,
                                 committer_name = options.commname,
                                 committer_email = options.commemail,
                                 backup = True, sign_str = sign_str,
                                 notes = options.annotate)

        if crt_series.empty_patch(patch):
            out.done('empty patch')
        else:
            out.done()

        if options.patch:
            between.reverse()
            push_patches(between)
    elif options.annotate:
        # only annotate the top log entry as there is no need to
        # refresh the patch and generate a full commit
        crt_series.log_patch(crt_series.get_patch(patch), None,
                             notes = options.annotate)
    else:
        out.info('Patch "%s" is already up to date' % patch)
