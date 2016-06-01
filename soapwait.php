<?php

require_once("BootMini.php");

$cmService = new services_COMCOL_CmTopology();
$cmProc    = new services_COMCOL_CmProcMgr();

$found = 0;

print "Waiting for apwSoapServer to become ready on NOA...\n";

while(!$found) {
    print ".";
    $procs = $cmProc->getData();
    if (array_key_exists("procs", $procs)) {
        $procs = $procs->procs;
    }
    foreach($procs as $proc) {
        if ($proc->procTag == "apwSoapServer" && $proc->state == "cm:Up") {
            print "got it!\n";
            $found = 1;
        }
    }
    sleep(5);
}
sleep(10);
