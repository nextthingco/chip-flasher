#!/bin/bash
echo `hostname`
cd ~
DIRECTORY="CHIP-nandTests"
if [ ! -d "$DIRECTORY" ]; then
nm-online -q -t 30 || { echo "Failed"; exit 1; }
 apt-get update
 apt-get install --yes --force-yes git bonnie++ 
 git clone https://%NAND_REPO_USER%:%NAND_REPO_PASSWORD%@github.com/NextThingCo/$DIRECTORY.git
fi
cd $DIRECTORY

#wait for a connection
nm-online -q -t 45 || { echo "failed to connect to wifi"; exit -1; }

git pull https://%NAND_REPO_USER%:%NAND_REPO_PASSWORD%@github.com/NextThingCo/$DIRECTORY

if [[ -f runAtBoot.sh ]]; then
bash runAtBoot.sh
fi

#determine which test to run using a modulus of the hostnames number by the number of tests
COUNT=$(hostname | cut -c4-6)
COUNT=$((10#$COUNT))
TEST_COUNT=$(ls test_*.sh | wc -l)
TEST_NUM=$((($COUNT % $TEST_COUNT) +1))
TEST_NAME=$(ls -1 test_*.sh | sed "$TEST_NUM q;d")
PREVIOUS_TEST_NAME="none"
if [[ -f testname ]]; then
PREVIOUS_TEST_NAME=$(< testname)
fi

if [ $TEST_NAME != $PREVIOUS_TEST_NAME ]; then
	echo $TEST_NAME > testname
	systemctl disable bootstrap.service
	systemctl disable testStress.service
	if [$TEST_NAME == "test_nand_stress.sh"]; then
	 systemctl enable testStress.service
	else
	 systemctl enable bootstrap.service
	fi
	reboot	
fi			
echo Running test $TEST_NAME		 
bash $TEST_NAME