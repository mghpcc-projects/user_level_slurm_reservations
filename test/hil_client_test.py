"""
General info about these tests

The tests assusme that the nodes are in the <from_project> which is set to be the
"slurm" project, since that is what we are testing here.

If all tests pass successfully, then nodes are back in their original state.

Class TestHILReserve moves nodes out of the slurm project and into the free pool;
and TestHILRelease puts nodes back into the slurm project from the free pool

run the tests like this
py.test <path to testfile>
py.test hil_client_test
"""

import inspect
import sys
import pytest
import requests
from os.path import realpath, dirname, isfile, join
import uuid

libdir = realpath(join(dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)

import hil_slurm_client


# Some constants useful for tests
nodelist = ['slurm-compute1', 'slurm-compute2', 'slurm-compute3']
hil_client = hil_slurm_client.hil_init()
to_project = 'slurm'
from_project = 'slurm'

bad_hil_client = hil_slurm_client.hil_client_connect('http://127.3.2.1',
                                                     'baduser', 'badpassword')


class TestHILReserve:
    """Tests various hil_reserve cases"""

    def test_hil_reserve_success(self):
        """test the regular success scenario"""

        # should raise an error if <from_project> doesn't add up.
        with pytest.raises(hil_slurm_client.ProjectMismatchError):
            random_project = str(uuid.uuid4())
            hil_slurm_client.hil_reserve_nodes(nodelist, random_project, hil_client)

        # should run without any errors
        hil_slurm_client.hil_reserve_nodes(nodelist, from_project, hil_client)

        # should raise error if a bad hil_client is passed
        with pytest.raises(requests.ConnectionError):
            hil_slurm_client.hil_reserve_nodes(nodelist, from_project, bad_hil_client)


class TestHILRelease:
    """Test various hil_release cases"""
    def test_hil_release(self):
        # should raise error if a bad hil_client is passed
        with pytest.raises(requests.ConnectionError):
            hil_slurm_client.hil_free_nodes(nodelist, to_project, bad_hil_client)

        # calling it with a functioning hil_client should work
        hil_slurm_client.hil_free_nodes(nodelist, to_project, hil_client)

        # At this point, nodes are already owned by the <to_project>
        # calling it again should have no affect.
        hil_slurm_client.hil_free_nodes(nodelist, to_project, hil_client)

