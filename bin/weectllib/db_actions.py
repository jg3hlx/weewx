#
#    Copyright (c) 2009-2023 Tom Keffer <tkeffer@gmail.com> and Matthew Wall
#
#    See the file LICENSE.txt for your rights.
#
"""Various high-level, interactive, database actions"""

import datetime
import logging
import sys
import time

import weecfg
import weectllib
import weedb
import weewx.manager
from weeutil.weeutil import bcolors, y_or_n

log = logging.getLogger(__name__)


def create_database(config_path, db_binding='wx_binding', dry_run=False):
    """Create a new database."""
    if dry_run:
        print("This is a dry run. Nothing will actually be done.")

    config_path, config_dict = weecfg.read_config(config_path)

    print(f"The configuration file {bcolors.BOLD}{config_path}{bcolors.ENDC} will be used.")

    # Try a simple open. If it succeeds, that means the database
    # exists and is initialized. Otherwise, an exception will be raised.
    try:
        with weewx.manager.open_manager_with_config(config_dict, db_binding) as dbmanager:
            print(f"Database '{dbmanager.database_name}' already exists. Nothing done.")
    except weedb.OperationalError:
        if not dry_run:
            # Database does not exist. Try again, but allow initialization:
            with weewx.manager.open_manager_with_config(config_dict,
                                                        db_binding,
                                                        initialize=True) as dbmanager:
                print(f"Created database '{dbmanager.database_name}'.")


def drop_daily(config_path, db_binding='wx_binding', dry_run=False):
    """Drop the daily summary from a WeeWX database."""
    if dry_run:
        print("This is a dry run. Nothing will actually be done.")

    config_path, config_dict = weecfg.read_config(config_path)

    print(f"The configuration file {bcolors.BOLD}{config_path}{bcolors.ENDC} will be used.")

    manager_dict = weewx.manager.get_manager_dict_from_config(config_dict, db_binding)
    database_name = manager_dict['database_dict']['database_name']

    print(f"Proceeding will delete all your daily summaries from database '{database_name}'")
    ans = y_or_n("Are you sure you want to proceed (y/n)? ")
    if ans == 'y':
        t1 = time.time()
        print(f"Dropping daily summary tables from '{database_name}' ... ")
        try:
            with weewx.manager.open_manager_with_config(config_dict, db_binding) as dbmanager:
                try:
                    if not dry_run:
                        dbmanager.drop_daily()
                except weedb.OperationalError as e:
                    print("Error '%s'" % e, file=sys.stderr)
                    print(f"Drop daily summary tables failed for database '{database_name}'")
                else:
                    tdiff = time.time() - t1
                    print("Daily summary tables dropped from "
                          f"database '{database_name}' in {tdiff:.2f} seconds")
        except weedb.OperationalError:
            # No daily summaries. Nothing to be done.
            print(f"No daily summaries found in database '{database_name}'. Nothing done.")
    else:
        print("Nothing done.")

    if dry_run:
        print("This was a dry run. Nothing was actually done.")


def rebuild_daily(config_path,
                  db_binding='wx_binding',
                  date=None,
                  from_date=None,
                  to_date=None,
                  dry_run = False):
    """Rebuild the daily summaries."""

    if dry_run:
        print("This is a dry run. Nothing will actually be done.")

    config_path, config_dict = weecfg.read_config(config_path)

    print(f"The configuration file {bcolors.BOLD}{config_path}{bcolors.ENDC} will be used.")

    manager_dict = weewx.manager.get_manager_dict_from_config(config_dict,
                                                              db_binding)
    database_name = manager_dict['database_dict']['database_name']

    # Get any dates the user might have specified.
    from_d, to_d = weectllib.parse_dates(date, from_date, to_date)

    # Advise the user/log what we will do
    if not from_d and not to_d:
        msg = "All daily summaries will be rebuilt."
    elif from_d and not to_d:
        msg = f"Daily summaries starting with {from_d} will be rebuilt."
    elif not from_d and to_d:
        msg = f"Daily summaries through {to_d} will be rebuilt."
    elif from_d == to_d:
        msg = f"Daily summary for {from_d} will be rebuilt."
    else:
        msg = f"Daily summaries from {from_d} through {to_d}, inclusive, will be rebuilt."

    log.info(msg)
    print(msg)
    ans = y_or_n(f"Rebuild the daily summaries in the database '{database_name}'? (y/n) ")
    if ans == 'n':
        log.info("Nothing done.")
        print("Nothing done.")
        return

    t1 = time.time()

    log.info("Rebuilding daily summaries in database '%s' ..." % database_name)
    print("Rebuilding daily summaries in database '%s' ..." % database_name)
    if dry_run:
        print("This was a dry run. Nothing was actually done.")
        return

    # Open up the database. This will create the tables necessary for the daily
    # summaries if they don't already exist:
    with weewx.manager.open_manager_with_config(config_dict,
                                                db_binding, initialize=True) as dbmanager:
        # Do the actual rebuild
        nrecs, ndays = dbmanager.backfill_day_summary(start_d=from_d,
                                                      stop_d=to_d,
                                                      trans_days=20)
    tdiff = time.time() - t1
    # advise the user/log what we did
    log.info("Rebuild of daily summaries in database '%s' complete." % database_name)
    if nrecs:
        sys.stdout.flush()
        # fix a bit of formatting inconsistency if less than 1000 records
        # processed
        if nrecs >= 1000:
            print()
        if ndays == 1:
            msg = f"Processed {nrecs} records to rebuild 1 daily summary in {tdiff:.2f} seconds."
        else:
            msg = f"Processed {nrecs} records to rebuild {ndays} daily summaries in "\
                    "{tdiff:.2f} seconds."
        print(msg)
        print(f"Rebuild of daily summaries in database '{database_name}' complete.")
    else:
        print(f"Daily summaries up to date in '{database_name}'.")