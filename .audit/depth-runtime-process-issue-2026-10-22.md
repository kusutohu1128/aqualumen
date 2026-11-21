# Owned process guard scope

Observed unrelated Android Gradle/Kotlin Java processes during depth preflight. The existing display/paired runtime checks reject every Java process globally. Do not stop or modify those unrelated processes.

The new depth runtime adapter scopes stopped/live checks to same-user Java processes whose exact current working directory is the canonical Lab path. Multiple Lab processes fail closed. Permission errors establishing same-user ownership fail closed. Existing exact-world/config/pack/Mod/ordinary-save checks and cooperative quit remain unchanged. No process termination was added. The old evidence-bound runtime files are unchanged.

Pure tests cover unrelated Java exclusion and multiple-owned-process preservation. Actual launch/restore still requires exact Lab process identity and all previous runtime guards.

After actual Claude review, the adapter was widened to path resolution/inode ancestry, command argument and open-FD references. It is no longer the first exact-text-cwd-only version described above. Three tests cover aliases, arguments, open files, unrelated Java and multiple Lab JVMs. No unrelated process termination was added.
