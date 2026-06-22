"""Tests for agent_fs."""
import pytest
from pathlib import Path

from agent_fs import AgentFS, AgentFSError, CommitError, RefNotFoundError
from agent_fs.exceptions import FileNotFoundError as AgentFSFileNotFoundError


@pytest.fixture
def fs(tmp_path):
    return AgentFS(tmp_path, "subject-1")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_root_created(self, tmp_path):
        fs = AgentFS(tmp_path, "alice")
        assert (tmp_path / "alice").is_dir()
        assert (tmp_path / "alice" / ".git").is_dir()

    def test_root_path(self, tmp_path):
        fs = AgentFS(tmp_path, "bob")
        assert fs.root == tmp_path / "bob"

    def test_idempotent_init(self, tmp_path):
        AgentFS(tmp_path, "carol")
        # Second construction should not raise
        fs2 = AgentFS(tmp_path, "carol")
        assert fs2.root.exists()

    def test_initial_head_exists(self, fs):
        assert len(fs.head()) == 40


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

class TestReadWrite:
    def test_write_and_read(self, fs):
        fs.write("hello.txt", "world")
        assert fs.read("hello.txt") == "world"

    def test_write_creates_directories(self, fs):
        fs.write("a/b/c.txt", "nested")
        assert (fs.root / "a" / "b" / "c.txt").exists()

    def test_read_missing_raises(self, fs):
        with pytest.raises(AgentFSFileNotFoundError):
            fs.read("missing.txt")

    def test_write_bytes(self, fs):
        data = b"\x00\x01\x02"
        fs.write("bin.dat", data)
        assert fs.read_bytes("bin.dat") == data

    def test_write_no_commit(self, fs):
        h1 = fs.head()
        fs.write("x.txt", "content", auto_commit=False)
        assert fs.head() == h1  # HEAD unchanged

    def test_overwrite(self, fs):
        fs.write("f.txt", "v1")
        fs.write("f.txt", "v2")
        assert fs.read("f.txt") == "v2"

    def test_path_escape_raises(self, fs):
        with pytest.raises(AgentFSError):
            fs.read("../../etc/passwd")


# ---------------------------------------------------------------------------
# Delete / move / copy
# ---------------------------------------------------------------------------

class TestDeleteMoveCopy:
    def test_delete(self, fs):
        fs.write("del.txt", "bye")
        fs.delete("del.txt")
        assert not fs.exists("del.txt")

    def test_delete_missing_raises(self, fs):
        with pytest.raises(AgentFSFileNotFoundError):
            fs.delete("nope.txt")

    def test_move(self, fs):
        fs.write("src.txt", "data")
        fs.move("src.txt", "dst.txt")
        assert fs.read("dst.txt") == "data"
        assert not fs.exists("src.txt")

    def test_copy(self, fs):
        fs.write("orig.txt", "copy-me")
        fs.copy("orig.txt", "clone.txt")
        assert fs.read("orig.txt") == "copy-me"
        assert fs.read("clone.txt") == "copy-me"

    def test_mkdir(self, fs):
        fs.mkdir("subdir/nested")
        assert (fs.root / "subdir" / "nested").is_dir()


# ---------------------------------------------------------------------------
# exists / is_dir / list
# ---------------------------------------------------------------------------

class TestFilesystem:
    def test_exists_true(self, fs):
        fs.write("e.txt", "x")
        assert fs.exists("e.txt")

    def test_exists_false(self, fs):
        assert not fs.exists("nope.txt")

    def test_is_dir(self, fs):
        fs.mkdir("mydir")
        assert fs.is_dir("mydir")
        assert not fs.is_dir("nope")

    def test_list_root(self, fs):
        fs.write("a.txt", "")
        fs.write("b.txt", "")
        entries = fs.list()
        assert "a.txt" in entries
        assert "b.txt" in entries

    def test_list_recursive(self, fs):
        fs.write("x/y/z.txt", "deep")
        entries = fs.list(recursive=True)
        assert any("z.txt" in e for e in entries)

    def test_list_subdir(self, fs):
        fs.write("sub/file.txt", "")
        entries = fs.list("sub")
        assert "sub/file.txt" in entries


# ---------------------------------------------------------------------------
# Commit / status / head
# ---------------------------------------------------------------------------

class TestCommit:
    def test_explicit_commit(self, fs):
        fs.write("c.txt", "v1", auto_commit=False)
        fs.stage("c.txt")
        h = fs.commit("explicit commit")
        assert len(h) == 40

    def test_status_after_unstaged_change(self, fs):
        fs.write("s.txt", "v1")
        # Modify without committing
        (fs.root / "s.txt").write_text("v2")
        entries = fs.status()
        paths = [e.path for e in entries]
        assert "s.txt" in paths

    def test_status_clean(self, fs):
        fs.write("clean.txt", "data")
        assert fs.status() == []

    def test_head_changes_on_commit(self, fs):
        h1 = fs.head()
        fs.write("h.txt", "x")
        h2 = fs.head()
        assert h1 != h2


# ---------------------------------------------------------------------------
# Log / diff
# ---------------------------------------------------------------------------

class TestLogDiff:
    def test_log_returns_commits(self, fs):
        fs.write("l1.txt", "a")
        fs.write("l2.txt", "b")
        commits = fs.log()
        assert len(commits) >= 2

    def test_log_limit(self, fs):
        for i in range(5):
            fs.write(f"f{i}.txt", str(i))
        commits = fs.log(limit=3)
        assert len(commits) == 3

    def test_log_file_filter(self, fs):
        fs.write("only_this.txt", "v1")
        fs.write("other.txt", "v2")
        fs.write("only_this.txt", "v3")
        commits = fs.log(file_path="only_this.txt")
        for c in commits:
            assert "only_this.txt" in c.files_changed

    def test_diff_unstaged(self, fs):
        fs.write("d.txt", "original")
        (fs.root / "d.txt").write_text("modified")
        patch = fs.diff("d.txt")
        assert "modified" in patch

    def test_diff_staged(self, fs):
        fs.write("staged.txt", "old")
        (fs.root / "staged.txt").write_text("new")
        fs.stage("staged.txt")
        patch = fs.diff("staged.txt", staged=True)
        assert "new" in patch


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

class TestBranches:
    def test_current_branch(self, fs):
        branch = fs.current_branch()
        assert isinstance(branch, str)
        assert len(branch) > 0

    def test_create_and_list_branches(self, fs):
        fs.create_branch("feature-x")
        assert "feature-x" in fs.branches()

    def test_checkout_branch(self, fs):
        fs.create_branch("dev")
        fs.checkout("dev")
        assert fs.current_branch() == "dev"

    def test_create_checkout_new_branch(self, fs):
        fs.checkout("new-branch", create=True)
        assert fs.current_branch() == "new-branch"

    def test_delete_branch(self, fs):
        fs.create_branch("to-delete")
        fs.delete_branch("to-delete")
        assert "to-delete" not in fs.branches()

    def test_checkout_file_at_ref(self, fs):
        fs.write("ver.txt", "version-1")
        ref = fs.head()
        fs.write("ver.txt", "version-2")
        fs.checkout(ref, file_path="ver.txt")
        assert fs.read("ver.txt") == "version-1"

    def test_merge(self, fs):
        main = fs.current_branch()
        fs.write("base.txt", "base")
        fs.create_branch("side")
        fs.checkout("side")
        fs.write("side.txt", "side-content")
        fs.checkout(main)
        fs.merge("side")
        assert fs.read("side.txt") == "side-content"


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TestTags:
    def test_create_and_list_tag(self, fs):
        fs.write("tagged.txt", "v1")
        fs.tag("v1.0")
        assert "v1.0" in fs.tags()

    def test_annotated_tag(self, fs):
        fs.write("ann.txt", "data")
        fs.tag("v2.0", message="Release 2.0")
        assert "v2.0" in fs.tags()

    def test_delete_tag(self, fs):
        fs.write("t.txt", "x")
        fs.tag("tmp")
        fs.delete_tag("tmp")
        assert "tmp" not in fs.tags()


# ---------------------------------------------------------------------------
# read_at / restore / revert / cherry_pick
# ---------------------------------------------------------------------------

class TestVersionedFileOps:
    def test_read_at(self, fs):
        fs.write("versioned.txt", "v1")
        ref = fs.head()
        fs.write("versioned.txt", "v2")
        assert fs.read_at("versioned.txt", ref) == "v1"

    def test_read_at_invalid_ref_raises(self, fs):
        fs.write("x.txt", "data")
        with pytest.raises(RefNotFoundError):
            fs.read_at("x.txt", "deadbeef1234567890deadbeef1234567890dead")

    def test_restore(self, fs):
        fs.write("restore_me.txt", "original")
        ref = fs.head()
        fs.write("restore_me.txt", "changed")
        fs.restore("restore_me.txt", ref)
        assert fs.read("restore_me.txt") == "original"

    def test_revert(self, fs):
        fs.write("rev.txt", "before")
        fs.write("rev.txt", "bad-change")
        bad = fs.head()  # commit that introduced "bad-change"
        fs.revert(bad)
        assert fs.read("rev.txt") == "before"

    def test_cherry_pick(self, fs):
        main = fs.current_branch()
        fs.write("cherry.txt", "base")
        fs.create_branch("work")
        fs.checkout("work")
        fs.write("cherry.txt", "feature")
        feature_hash = fs.head()
        fs.checkout(main)
        fs.cherry_pick(feature_hash)
        assert fs.read("cherry.txt") == "feature"


# ---------------------------------------------------------------------------
# Stash
# ---------------------------------------------------------------------------

class TestStash:
    def test_stash_and_pop(self, fs):
        fs.write("stashed.txt", "committed")
        (fs.root / "stashed.txt").write_text("uncommitted-change")
        fs.stash()
        # Working tree should be clean after stash
        assert fs.read("stashed.txt") == "committed"
        fs.stash_pop()
        assert fs.read("stashed.txt") == "uncommitted-change"

    def test_stash_list(self, fs):
        fs.write("s.txt", "v1")
        (fs.root / "s.txt").write_text("dirty")
        fs.stash(message="my stash")
        entries = fs.stash_list()
        assert len(entries) >= 1
        assert any("my stash" in e["message"] for e in entries)

    def test_stash_drop(self, fs):
        fs.write("d.txt", "v1")
        (fs.root / "d.txt").write_text("dirty")
        fs.stash()
        fs.stash_drop()
        assert fs.stash_list() == []


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

class TestInfo:
    def test_info_keys(self, fs):
        info = fs.info()
        assert "root" in info
        assert "branch" in info
        assert "head" in info
        assert "branches" in info
        assert "tags" in info
        assert "status" in info
