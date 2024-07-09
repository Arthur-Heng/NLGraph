#!/usr/bin/perl
#
# $Id: asrank.pl,v 1.1 2013/08/20 20:49:32 macat Exp $
#
# Copyright (C) 2012-2013 The Regents of the University of California.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# mjl

use strict;
use warnings;
use diagnostics;
use Getopt::Long qw(GetOptions);
use IPC::Open2 qw(open2);
use IO::Handle qw( );

STDOUT->autoflush(1);
STDERR->autoflush(1);

my $ixp_string;
my $clique_string;
my $exclvps_string;
my $filtered_flag = '';
my $verbose = '';
my $result = GetOptions("ixp=s" => \$ixp_string,
			"clique=s" => \$clique_string,
			"verbose" => \$verbose,
			"exclvps=s" => \$exclvps_string,
			"filtered" => \$filtered_flag);

if(!$result || $#ARGV < 0)
{
    print STDERR "usage: asrank.pl [--ixp \$ixps] [--exclvps \$exclvps] [--clique \$clique] [--filtered] \$paths [opt]\n";
    exit -1;
}

my $paths = $ARGV[0];
my $opt   = $ARGV[1] if($#ARGV >= 1);
my $pass  = 0;
my %ixp;
my %data;
my %clique;
my %vpoc;
my %r;

# if the user specified a set of IXP ASes, put them in a hash table now.
if(defined($ixp_string))
{
    if(-r $ixp_string)
    {
	open(IX, $ixp_string) or die "could not open $ixp_string";
	while(<IX>)
	{
	    $ixp{$1} = 1 if(/^(\d+)/);
	}
	close IX;
    }
    elsif($ixp_string =~ /^[\d\s]+$/)
    {
	$ixp{$_} = 1 foreach(split(/\s+/, $ixp_string));
    }
    else
    {
	print STDERR "invalid ixp parameter\n";
	exit -1;
    }
}

my %exclvps;
if(defined($exclvps_string))
{
    $exclvps{$_} = 1 foreach(split(/\s+/, $exclvps_string));
}

$opt = "rels" if(!defined($opt));

sub custcone($$);
sub custcone($$)
{
    my ($a, $b) = @_;

    if(!defined($data{$a}{cone}{$b}))
    {
	$data{$a}{cone}{$b}++;

	foreach my $c (keys %{$data{$b}{cone}})
	{
	    $data{$a}{cone}{$c} += $data{$b}{cone}{$c};
	}
	return if(!defined($data{$a}{provs}));
	foreach my $p (keys %{$data{$a}{provs}})
	{
	    custcone($p, $b);
	}
    }

    return;
}

#
# set a relationship between two ASes.
#
sub r($$$)
{
    my ($a, $b, $r) = @_;

    if(defined($r{$a}{$b}))
    {
	print STDERR "fatal: a relationship already exists for $a + $b\n";
	exit -1;
    }

    print "# $a/$b/$r\n" if($verbose);

    if($r == -1)   #p2c
    {
	$data{$b}{provs}{$a} = 1;
	$data{$a}{custs}{$b} = 1;
	custcone($a, $b);
    }
    elsif($r == 0) #p2p
    {
	$data{$b}{peers}{$a} = 1;
	$data{$a}{peers}{$b} = 1;
    }
    elsif($r == 2) #s2s
    {
	$data{$a}{sibls}{$b} = 1;
	$data{$b}{sibls}{$a} = 1;
    }
    $r{$a}{$b} = $r;
    $r{$b}{$a} = ($r != -1) ? $r : 1;
    return;
}

sub clique($)
{
    my ($as) = @_;
    return defined($clique{$as});
}

sub p2c_ok($$)
{
    my ($x, $y) = @_;
    return 0 if(clique($y));
    return 1 if(!defined($data{$y}{cone}));
    return 0 if(defined($data{$y}{cone}{$x}));
    return 1;
}

sub c2p($$)
{
    my ($x, $y) = @_;
    return 0 if(!defined($r{$x}{$y}) || $r{$x}{$y} != 1);
    return 1;
}

sub p2p($$)
{
    my ($x, $y) = @_;
    return 0 if(!defined($r{$x}{$y}) || $r{$x}{$y} != 0);
    return 1;
}

sub p2c($$)
{
    my ($x, $y) = @_;
    return 0 if(!defined($r{$x}{$y}) || $r{$x}{$y} != -1);
    return 1;
}

sub global_degree($)
{
    my ($as) = @_;
    return 0 if(!defined($data{$as}{links}));
    return scalar(keys %{$data{$as}{links}});
}

sub transit_degree($)
{
    my ($as) = @_;
    return 0 if(!defined($data{$as}{trans}));
    return scalar(keys %{$data{$as}{trans}});
}

sub provider_degree($)
{
    my ($as) = @_;
    return 0 if(!defined($data{$as}{provs}));
    return scalar(keys %{$data{$as}{provs}});
}

sub peer_degree($)
{
    my ($as) = @_;
    return 0 if(!defined($data{$as}{peers}));
    return scalar(keys %{$data{$as}{peers}});
}

sub link_degree($$)
{
    my ($a, $b) = @_;
    return 0 if(!defined($data{$a}{trips}));
    return 0 if(!defined($data{$a}{trips}{$b}));
    return scalar(keys %{$data{$a}{trips}{$b}});
}

sub trip_sum($$$)
{
    my ($x, $y, $z) = @_;
    my $s = 0;
    return 0 if(!defined($data{$x}{quads}));
    return 0 if(!defined($data{$x}{quads}{$y}));
    return 0 if(!defined($data{$x}{quads}{$y}{$z}));
    foreach (keys %{$data{$x}{quads}{$y}{$z}})
    {
	$s += $data{$x}{quads}{$y}{$z}{$_};
    }
    return $s;
}

sub trip_degree($$$)
{
    my ($x, $y, $z) = @_;
    return 0 if(!defined($data{$x}{quads}));
    return 0 if(!defined($data{$x}{quads}{$y}));
    return 0 if(!defined($data{$x}{quads}{$y}{$z}));
    return scalar(keys %{$data{$x}{quads}{$y}{$z}});
}

sub trip_z($$$)
{
    my ($x, $y, $z) = @_;
    return 0 if(!defined($data{$x}{trip_z}));
    return 0 if(!defined($data{$x}{trip_z}{$y}));
    return 0 if(!defined($data{$x}{trip_z}{$y}{$z}));
    return $data{$x}{trip_z}{$y}{$z};
}

sub upstr_c($$$)
{
    my ($x, $y, $z) = @_;
    return 0 if(!defined($data{$x}{upstr}));
    return 0 if(!defined($data{$x}{upstr}{$y}));
    return 0 if(!defined($data{$x}{upstr}{$y}{$z}));
    return $data{$x}{upstr}{$y}{$z};
}

sub trips_c($$$)
{
    my ($x, $y, $z) = @_;
    return 0 if(!defined($data{$x}{trips}));
    return 0 if(!defined($data{$x}{trips}{$y}));
    return 0 if(!defined($data{$x}{trips}{$y}{$z}));
    return $data{$x}{trips}{$y}{$z};
}

sub peerrank($$$)
{
    my ($a, $b, $x) = @_;
    my ($i, $j);

    $i = link_degree($x, $a);
    $j = link_degree($x, $b);
    return -1 if($i > $j);
    return  1 if($i < $j);

    $i = link_degree($a, $x);
    $j = link_degree($b, $x);
    return -1 if($i < $j);
    return  1 if($i > $j);

    $i = transit_degree($a);
    $j = transit_degree($b);
    return -1 if($i > $j);
    return  1 if($i < $j);

    $i = global_degree($a);
    $j = global_degree($b);
    return -1 if($i > $j);
    return  1 if($i < $j);

    return 0;
}

sub top_down($$)
{
    my ($a, $b) = @_;
    my ($at, $bt, $ag, $bg, $ac, $bc);

    # push members of the clique to the top, if we know who they are.
    $ac = clique($a) ? 1 : 0;
    $bc = clique($b) ? 1 : 0;
    if($ac != 0 || $bc != 0)
    {
	return -1 if($ac > $bc);
	return  1 if($ac < $bc);
    }

    $at = transit_degree($a);
    $bt = transit_degree($b);
    $ag = global_degree($a);
    $bg = global_degree($b);

    return -1 if($at > $bt);
    return  1 if($at < $bt);
    return -1 if($ag > $bg);
    return  1 if($ag < $bg);
    return -1 if($a < $b);
    return  1 if($a > $b);
    return 0;
}

sub parse_path($)
{
    my ($path) = @_;
    if($path =~ /^#/ || $path =~ /\|\|/)
    {
	return ();
    }

    my @path = split(/\|/, $path);
    return @path if($filtered_flag);

    # skip over path if the VP is to be excluded.
    return () if(defined($exclvps{$path[0]}));

    my %ases;
    my $clique = 0;
    my @np;
    foreach my $i (0 .. $#path)
    {
	my $as = $path[$i];

	# reserved ASN
	if($as == 0 || $as == 23456 || $as >= 394240 ||
	   ($as >= 61440  && $as <= 131071) ||
	   ($as >= 133120 && $as <= 196607) ||
	   ($as >= 199680 && $as <= 262143) ||
	   ($as >= 263168 && $as <= 327679) ||
	   ($as >= 328704 && $as <= 393215))
	{
	    return ();
	}

	# skip over IXP ASes.
	next if(defined($ixp{$as}));

	# loop detection
	return () if(defined($ases{$as}));
	$ases{$as} = 1;
	push @np, $as;

	# detect and discard invalid paths (probably caused by poisoning)
	# where a clique AS is inserted into a poisoned path.
	if(clique($as))
	{
	    return () if($clique != 0 && !clique($path[$i-1]));
	    $clique = 1;
	}
    }

    return @np;
}

sub read_paths
{
    # empty out the data hash table.
    %data = (); %vpoc = ();

    if($paths =~ /\.bz2$/)
    {
	open(PATHS, "bzcat $paths |") or die "could not open $paths";
    }
    else
    {
	open(PATHS, $paths) or die "could not open $paths";
    }
    while(<PATHS>)
    {
	chomp;

	# skip over comments.
	if(/^#/)
	{
	    next if($pass != 0);
	    print "$_\n";
	    if($_ =~ /^# inferred clique: (.+)$/)
	    {
		$clique{$_} = 1 foreach(split(/\s+/, $1));
	    }
	    next;
	}

	my @path = parse_path($_);
	next if($#path == -1);

	# count how many origins this VP can reach.
	$vpoc{$path[0]}{$path[$#path]}++;
	$data{$path[0]}{vp}{$path[1]}{$path[2]}++ if($#path == 2);

	foreach my $i (1 .. $#path)
	{
	    my $a = $path[$i-1];
	    my $x = $path[$i];

	    $data{$a}{links}{$x}++;
	    $data{$x}{links}{$a}++;

	    if($i < $#path)
	    {
		my $b = $path[$i+1];
		$data{$b}{links}{$x}++;
		$data{$x}{links}{$b}++;
		$data{$x}{trans}{$a}++;
		$data{$x}{trans}{$b}++;
		$data{$a}{trips}{$x}{$b}++;
		$data{$b}{trips}{$x}{$a}++;
		$data{$b}{upstr}{$x}{$a}++;
		$data{$x}{povup}{$a}{$b}++;

		if($i+1 < $#path)
		{
		    my $c = $path[$i+2];
		    $data{$a}{quads}{$x}{$b}{$c}++;
		}
		else
		{
		    $data{$a}{trip_z}{$x}{$b}++;
		}
	    }
	}
    }
    close PATHS;

    $pass++;
    return;
}

sub rank_peers
{
    foreach my $as (keys %data)
    {
	my @ranking = sort { peerrank($a, $b, $as) } keys %{$data{$as}{links}};
	@{$data{$as}{ranking}} = @ranking;
	foreach my $i (0 .. $#ranking)
	{
	    my $x = $ranking[$i];
	    $data{$as}{rank}{$x} = $i + 1;
	}
    }
}

#
# select providers from a set of neighbours.  this function will only
# select a provider from a set of ASes if it has a larger transit degree
# than AS x due to the way it is invoked.
#
sub select_providers($)
{
    my ($x) = @_; return if(clique($x));

    foreach my $y (sort top_down keys %{$data{$x}{links}})
    {
	next if(defined($r{$x}{$y}));

	my $r = 0;

	# does Y pass the route from X to a provider Z?
	if($r == 0 && provider_degree($y) > 0)
	{
	    foreach my $z (keys %{$data{$y}{provs}})
	    {
		if(upstr_c($x, $y, $z) > 0)
		{
		    $r = -1;
		    last;
		}
	    }
	}

	# does Y pass the route from X to peer Z?
	if($r == 0 && peer_degree($y) > 0)
	{
	    foreach my $z (keys %{$data{$y}{peers}})
	    {
		if(upstr_c($x, $y, $z) > 0)
		{
		    $r = -1;
		    last;
		}
		if(trips_c($x, $y, $z) > 2)
		{
		    $r = -1;
		    last;
		}
	    }
	}

	if($r == -1)
	{
	    next if(p2c_ok($y, $x) == 0);
	    r($y, $x, $r);
	}
    }

    return;
}

sub provider_to_larger_customer
{
    # collect a list of x:y:z triplets where x is a provider of y but no
    # relationship has been inferred for y:z because z has a larger transit
    # degree than y.  rank the triplets by the number of paths they appear
    # in, and then assign p2c relationships between y and z, and then
    # assign p2c relationships for y:z:zz triplets subsequent to that.
    # this part focuses only on cases where y has a smaller transit degree
    # because these are the only p2c relationships that would have been missed
    # in the first part.
    my %xyz;
    foreach my $x (keys %data)
    {
	next if(!defined($data{$x}{trips}));
	foreach my $y (keys %{$data{$x}{trips}})
	{
	    next if(!defined($r{$x}{$y}) || $r{$x}{$y} != -1);
	    foreach my $z (keys %{$data{$x}{trips}{$y}})
	    {
		next if(defined($r{$y}{$z}));
		next if(upstr_c($z, $y, $x) == 0);
		next if(trip_z($x, $y, $z) == 0);
		next if(transit_degree($y) > transit_degree($z));
		$xyz{"$x:$y:$z"} = $data{$x}{trips}{$y}{$z};
	    }
	}
    }
    while(scalar(keys %xyz) > 0)
    {
	my @xyz = sort {$xyz{$b} <=> $xyz{$a}} keys %xyz;
	my $xyz = $xyz[0];
	my $freq = $xyz{$xyz};
	my ($x, $y, $z) = split(/:/, $xyz[0]);

	delete $xyz{$xyz};

	next if($freq < 3);
	next if(defined($r{$y}{$z}));
	next if(p2c_ok($y, $z) == 0);

	r($y, $z, -1);
	foreach my $zz (keys %{$data{$z}{links}})
	{
	    next if(defined($r{$z}{$zz}));
	    next if(upstr_c($zz, $z, $y) == 0);
	    if(transit_degree($zz) > transit_degree($z))
	    {
		$xyz{"$y:$z:$zz"} = $data{$y}{trips}{$z}{$zz};
	    }
	    else
	    {
		next if(p2c_ok($z, $zz) == 0);
		r($z, $zz, -1);
	    }
	}
    }

    return;
}

sub provider_less_network($)
{
    my ($x) = @_;
    foreach my $y (sort top_down keys %{$data{$x}{links}})
    {
	next if(link_degree($y, $x) == 0);
	next if(defined($r{$x}{$y}));
	r($x, $y, 0);
	foreach my $z (keys %{$data{$y}{trips}{$x}})
	{
	    next if(defined($r{$x}{$z}));
	    next if(p2c_ok($x, $z) == 0);
	    r($x, $z, -1);

	    foreach my $zz (keys %{$data{$z}{links}})
	    {
		next if(defined($r{$z}{$zz}));
		next if(upstr_c($zz, $z, $x) == 0);
		if(transit_degree($zz) < transit_degree($z))
		{
		    next if(p2c_ok($z, $zz) == 0);
		    r($z, $zz, -1);
		}
	    }
	}
    }
    return;
}

# this method tries to fold sequences of p2p links
sub fold_p2p($)
{
    my ($x) = @_;
    my %p2p;

    # return now if this AS never appears in the middle of an AS path.
    return if(transit_degree($x) == 0);

    # determine candidate links that need to be folded.
    foreach my $y (keys %{$data{$x}{povup}})
    {
	next if(defined($r{$x}{$y}) && $r{$x}{$y} != 0);

	if(provider_degree($x) > 0)
	{
	    my $skip = 0;
	    foreach my $z (keys %{$data{$x}{provs}})
	    {
		if(trips_c($y, $x, $z) > 0)
		{
		    $skip = 1;
		    last;
		}
	    }
	    next if($skip != 0);
	}

	foreach my $z (keys %{$data{$x}{povup}{$y}})
	{
	    $p2p{$y}{$z} = 1 if(!defined($r{$x}{$z}));
	}
    }
    return if(scalar(keys %p2p) == 0);

    my %rhs;
    foreach my $y (keys %p2p)
    {
	$rhs{$_}++ foreach (keys %{$p2p{$y}});
    }
    foreach my $y (keys %p2p)
    {
	if(defined($rhs{$y}))
	{
	    delete $p2p{$y};
	    foreach my $z (keys %p2p)
	    {
		delete $p2p{$z}{$y} if(defined($p2p{$z}{$y}));
	    }
	}
    }
    %rhs = ();
    foreach my $y (keys %p2p)
    {
	$rhs{$_}++ foreach (keys %{$p2p{$y}});
    }
    foreach my $y (sort {$rhs{$b} <=> $rhs{$a}} keys %rhs)
    {
	next if(transit_degree($x) < transit_degree($y));
	next if(p2c_ok($x, $y) == 0);
	next if(defined($r{$x}{$y}));

	r($x, $y, -1);
	foreach my $z (keys %{$data{$y}{povup}{$x}})
	{
	    next if(defined($r{$y}{$z}));
	    next if(transit_degree($y) < transit_degree($z));
	    next if(p2c_ok($y, $z) == 0);
	    r($y, $z, -1);
	}
    }

    return;
}

sub td_sum
{
    my @as = @_; my $td = 0;
    $td += transit_degree($_) foreach (@as);
    return $td;
}

sub td_asn
{
    my ($x) = @_;
    return "$x:?" if(!defined($data{$x}));
    return sprintf("%d:%d", $x, transit_degree($x));
}

sub clique_link_hash($$$)
{
    my ($h, $y, $x) = @_;
    return 0 if(!defined($data{$x}{links}{$y}));

    my $verb = ($verbose && $opt eq "clique" ? 1 : 0);
    my $trip = 0;
    foreach my $z (keys %{$h})
    {
	next if($z == $y || $z == $x);

	if(upstr_c($x, $y, $z) > 0)
	{
	    my $td = trip_degree($z, $y, $x);
	    my $tz = trip_z($z, $y, $x);
	    printf("# tripdeg %d: %d|%d|%d %d %d %d:%d\n",
		   $x, $z, $y, $x, $td, $tz,
		   upstr_c($x, $y, $z), trip_sum($z, $y, $x))
		if($verb);
	    next if($td <= 5 && $tz == 0 &&
		    upstr_c($x, $y, $z) == trip_sum($z, $y, $x));
	    $trip = 1 if($td > 2);
	}
    }

    return 0 if($trip != 0);
    return 1;
}

sub clique_link_array($$$)
{
    my ($a, $z, $x) = @_;
    return 0 if(!defined($data{$x}{links}{$z}));

    my $trip = 0;
    my $verb = ($verbose && $opt eq "clique" ? 1 : 0);
    foreach my $y (@{$a})
    {
	next if($z == $y || $y == $x);

	if(upstr_c($x, $y, $z) > 0)
	{
	    my $td = trip_degree($z, $y, $x);
	    my $tz = trip_z($z, $y, $x);
	    printf("# tripdeg %d: %d|%d|%d %d %d %d:%d\n",
		   $x, $z, $y, $x, $td, $tz,
		   upstr_c($x, $y, $z), trip_sum($z, $y, $x))
		if($verb);
	    next if($td <= 5 && $tz == 0 &&
		    upstr_c($x, $y, $z) == trip_sum($z, $y, $x));
	    $trip = 1 if($td > 2);
	}
    }

    return 0 if($trip != 0);
    return 1;
}

sub python_clique
{
    my $verb = ($verbose && $opt eq "clique" ? 1 : 0);
    my @ases = sort {$a <=> $b} @_;
    my $pid;

    if($verb) {
	print  "# pyth: " . join (' ', @ases) . "\n";
	printf "#  %s\n", td_asn($_) foreach (@ases);
    }

    $pid = open2(\*PY_IN, \*PY_OUT, 'python');
    print PY_OUT "import graph\nx = graph.graph()\n";
    print PY_OUT "x.add_node($_)\n" foreach (@ases);

    foreach my $i (0 .. $#ases)
    {
	my $x = $ases[$i];
	foreach my $j ($i+1 .. $#ases)
	{
	    my $y = $ases[$j];
	    next if(clique_link_array(\@ases, $x, $y) == 0 ||
		    clique_link_array(\@ases, $y, $x) == 0);
	    print PY_OUT "x.add_edge($x, $y)\n";
	}
    }

    print PY_OUT "S = x.find_all_cliques()\n";
    print PY_OUT "for i in S:\n";
    print PY_OUT "  print i\n";
    close PY_OUT;

    my %cs;
    while(<PY_IN>)
    {
	chomp;
	if(/^set\(\[(.+)\]\)$/)
	{
	    my @x = split(/[\s,]+/, $1);
	    next if($#x < 0);
	    my $set = join(' ', sort {$a <=> $b} @x);
	    $cs{$set} = td_sum(@x);
	}
    }
    close PY_IN;
    waitpid($pid, 0);

    my @cs = sort {$cs{$b} <=> $cs{$a}} keys %cs;
    foreach my $set (@cs)
    {
	my @x = split(/ /, $set);
	print "# pytx: $set (" . td_sum(@x) . ")\n" if($verb);
    }
    return () if(scalar(@cs) < 1);
    return split(/ /, $cs[0]);
}

sub infer_clique($)
{
    my $verb = ($verbose && $opt eq "clique" ? 1 : 0);
    my ($N) = @_;
    my @rank = sort top_down keys %data;
    my %c1;
    my %c2;
    my %b;
    my $i = -1;

    while($i <= $#rank)
    {
	if($i == -1)
	{
	    my @N;
	    foreach my $i (0 .. $N-1)
	    {
		push @N, $rank[$i] if(!defined($b{$rank[$i]}));
	    }
	    @N = python_clique(@N);
	    return () if($#N < 0);
	    %c1 = ();
	    $c1{$_} = 0 foreach (@N);

	    if($verb)
	    {
		print "#  raw: " . join (' ', sort {$a <=> $b} @N) . "\n";
		foreach my $x (keys %c1)
		{
		    foreach my $y (keys %c1)
		    {
			next if($x == $y);
			foreach my $z (keys %c1)
			{
			    next if($x == $z || $y == $z);
			    next if(upstr_c($x, $y, $z) == 0);
			    printf("# tripraw: %d|%d|%d %d\n", $z, $y, $x,
				   trip_degree($z, $y, $x));
			}
		    }
		}
	    }

	    # $i++;
	    $i = $N;
	    next;
	}

	my $x = $rank[$i];
	if(defined($c1{$x}) || defined($b{$x}))
	{
	    $i++;
	    next;
	}
	last if(global_degree($x) < scalar(keys %c1));

	my @miss;
	foreach my $y (keys %c1)
	{
	    push @miss, $y if(clique_link_hash(\%c1, $y, $x) == 0);
	}
	if(scalar(@miss) > 0)
	{
	    printf("# missing-%d %d: %s\n", scalar(@miss), $x,
		   join(' ', sort {$a <=> $b} @miss)) if($verb);
	    $i++;
	    next;
	}

	$c1{$x} = $i;
	printf("#  add %s: %s\n", td_asn($x),
	       join(' ', sort {$a <=> $b} keys %c1))
	    if($verb);
	$i++;
    }

    print "# c1: " . join(' ', sort {$a <=> $b} keys %c1) . "\n";
    print "# c2: " . join(' ', sort {transit_degree($b) <=> transit_degree($a)} keys %c2) . "\n";

    return python_clique((keys %c1, keys %c2));
}

if($opt eq "clique")
{
    read_paths();
    my @c = infer_clique(10);
    print "# inferred clique: " . join(' ', sort {$a <=> $b} @c) . "\n";
    exit 0;
}

if($opt eq "table-transit-raw")
{
    read_paths();
    print "# ASN transit global\n";
    foreach my $x (sort top_down keys %data)
    {
	printf("%d %d %d\n", $x, transit_degree($x), global_degree($x));
    }
    exit 0;
}

#
# infer the clique at the top of the AS-level hierarchy by inferring a clique
# from the top 10 ASes (by transit degree) and then adding other ASes to it
# that do not break the clique.  then, re-read the paths: paths where
# members of the clique are disjoint are discarded.
#
if(defined($clique_string))
{
    $clique{$_} = 1 foreach(split(/\s+/, $clique_string));
}
elsif(!$filtered_flag)
{
    read_paths();
    my @c = infer_clique(10);
    $clique{$_} = 1 foreach(@c);
    print "# inferred clique: " . join(' ', sort {$a <=> $b} @c) . "\n";
    if(scalar(keys %ixp) > 0)
    {
	print "# IXP ASes: " . join(' ', sort {$a <=> $b} keys %ixp) . "\n";
    }
    if(scalar(keys %exclvps) > 0)
    {
	print "# Excluded VPs: " .
	    join(' ', sort {$a <=> $b} keys %exclvps) .
	    "\n";
    }
}

if($opt eq "filtered-paths" || $opt eq "filtered-out")
{
    if($paths =~ /\.bz2$/)
    {
	open(PATHS, "bzcat $paths |") or die "could not open $paths";
    }
    else
    {
	open(PATHS, $paths) or die "could not open $paths";
    }
    while(<PATHS>)
    {
	chomp;
	next if(/^#/);
	my @path = parse_path($_);
	if($#path == -1 && $opt eq "filtered-out")
	{
	    print "$_\n";
	}
	elsif($#path >= 0 && $opt eq "filtered-paths")
	{
	    print join('|', @path) . "\n";
	}
    }
    close PATHS;
    exit 0;
}

read_paths();

if($opt eq "rels")
{
    my $step = 1;

    # set peering in the clique
    printf("# step %d: set peering in clique\n", $step++) if($verbose);
    foreach my $x (sort {$a <=> $b} keys %clique)
    {
	foreach my $y (sort {$a <=> $b} keys %clique)
	{
	    r($x, $y, 0) if($x < $y);
	}
    }

    # assign providers.  these inferences have a 99.4% PPV.
    printf("# step %d: initial provider assignment\n", $step++) if($verbose);
    select_providers($_) foreach (sort top_down keys %data);

    # assign providers for stub ASes (transit degree zero), using the
    # assumption that a triplet observed by a VP which only supplies
    # routes to 5% of origin ASes is giving us routes from its customers
    # and peers, not its providers.  these inferences have a 100% PPV
    printf("# step %d: providers for stub ASes #1\n", $step++) if($verbose);
    foreach my $x (keys %vpoc)
    {
	next if(scalar(keys %{$vpoc{$x}}) * 50 > scalar(keys %data));
	foreach my $y (keys %{$data{$x}{vp}})
	{
	    foreach my $z (keys %{$data{$x}{vp}{$y}})
	    {
		next if(defined($r{$y}{$z}));
		next if(transit_degree($z) > 0);
		r($y, $z, -1);
	    }
	}
    }

    printf("# step %d: provider to larger customer\n", $step++) if($verbose);
    provider_to_larger_customer();

    # assemble a list of ASes that have no provider inferred, yet are not
    # part of the clique.  these are likely to be regional or R&E networks
    # that have no provider but do have customers.
    printf("# step %d: provider-less networks\n", $step++) if($verbose);
    foreach my $x (sort top_down keys %data)
    {
	next if(provider_degree($x) > 0 || clique($x));
	next if(transit_degree($x) < 10);
	provider_less_network($x);
    }

    printf("# step %d: c2p for stub-clique relationships\n", $step++) if($verbose);
    foreach my $x (keys %clique)
    {
	foreach my $y (keys %{$data{$x}{links}})
	{
	    next if(transit_degree($y) > 0);
	    next if(defined($r{$x}{$y}));
	    r($x, $y, -1);
	}
    }

    printf("# step %d: fold p2p links\n", $step++) if($verbose);
    foreach my $x (sort top_down keys %data)
    {
	fold_p2p($x);
    }

#    printf("# step %d: providers for stub ASes #2\n", $step++) if($verbose);
#    foreach my $x (keys %data)
#    {
#	next if(transit_degree($x) > 0);
#	foreach my $y (keys %{$data{$x}{trips}})
#	{
#	    next if(provider_degree($y) == 0);
#	    foreach my $z (keys %{$data{$y}{provs}})
#	    {
#		next if(defined($r{$x}{$y}));
#		next if(trips_c($x, $y, $z) == 0);
#		r($y, $x, -1);
#	    }
#	}
#    }

    printf("# step %d: everything else is p2p\n", $step++) if($verbose);
    foreach my $x (keys %data)
    {
	foreach my $y (keys %{$data{$x}{links}})
	{
	    next if(defined($r{$x}{$y}));
	    r($x, $y, 0);
	}
    }

    foreach my $x (sort {$a <=> $b} keys %r)
    {
	foreach my $y (sort {$a <=> $b} keys %{$r{$x}})
	{
	    next if($r{$x}{$y} == 1);
	    next if($r{$x}{$y} == 0 && $x > $y);
	    printf("%d|%d|%d\n", $x, $y, $r{$x}{$y});
	}
    }
}
elsif($opt eq "table-transit")
{
    print "# ASN transit global\n";
    foreach my $x (sort {transit_degree($b) <=> transit_degree($a)} keys %data)
    {
	printf("%d %d %d\n", $x, transit_degree($x), global_degree($x));
    }
}
elsif($opt eq "table-topdown")
{
    print "# ASN transit global\n";
    foreach my $x (sort top_down keys %data)
    {
	printf("%d %d %d\n", $x, transit_degree($x), global_degree($x));
    }
}
elsif($opt eq "table-rank")
{
    rank_peers();
    foreach my $x (sort {$a <=> $b} keys %data)
    {
	foreach my $y (@{$data{$x}{ranking}})
	{
	    printf("%d %d %d %d %d %d %d/%d\n",
		   $x, $y, global_degree($y), transit_degree($y),
		   link_degree($x, $y), link_degree($y, $x),
		   $data{$y}{rank}{$x}, global_degree($y));
	}
    }
}
elsif($opt eq "table-rank2")
{
    rank_peers();
    print "# from to from-local to-local from-rank to-rank\n";
    foreach my $x (sort {$a <=> $b} keys %data)
    {
	foreach my $y (sort {$a <=> $b} keys %{$data{$x}{links}})
	{
	    next if($x > $y);
	    printf("%d %d %d %d %d/%d %d/%d\n",
		   $x, $y, link_degree($x, $y), link_degree($y, $x),
		   $data{$x}{rank}{$y}, global_degree($x),
		   $data{$y}{rank}{$x}, global_degree($y));
	}
    }
}