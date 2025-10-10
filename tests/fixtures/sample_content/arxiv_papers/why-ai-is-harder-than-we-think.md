---
title: Why AI is Harder Than We Think
author: Melanie Mitchell
date: 2021-04-28
source_url: https://arxiv.org/abs/2104.12871
category: arxiv_paper
tags: ['Artificial Intelligence', 'Machine Learning', 'Common Sense', 'AI Predictions', 'Cognitive Science']
found_in: reading_08_diverse_perspectives_critics.md
---

# Why AI is Harder Than We Think

**Author:** Melanie Mitchell  
**Date:** 2021-04-28  
**Source:** [https://arxiv.org/abs/2104.12871](https://arxiv.org/abs/2104.12871)

## Summary

This paper discusses the cyclical nature of optimism and disappointment in AI development, highlighting four fallacies that contribute to overconfidence in AI predictions. It emphasizes the challenges of achieving human-like common sense in machines and the complexities of intelligence that are often underestimated.

---

--- Page 1 ---
arXiv:2104.12871v2  [cs.AI]  28 Apr 2021
Why AI is Harder Than We Think
Melanie Mitchell
Santa Fe Institute
Santa Fe, NM, USA
mm@santafe.edu
Abstract
Since its beginning in the 1950s, the ﬁeld of artiﬁcial intelligence has cy cled several times between periods
of optimistic predictions and massive investment (“AI spring”) and p eriods of disappointment, loss of conﬁ-
dence, and reduced funding (“AI winter”). Even with today’s seem ingly fast pace of AI breakthroughs, the
development of long-promised technologies such as self-driving car s, housekeeping robots, and conversational
companions has turned out to be much harder than many people exp ected. One reason for these repeating
cycles is our limited understanding of the nature and complexity of int elligence itself. In this paper I describe
four fallacies in common assumptions made by AI researchers, which can lead to overconﬁdent predictions
about the ﬁeld. I conclude by discussing the open questions spurre d by these fallacies, including the age-old
challenge of imbuing machines with humanlike common sense.
Introduction
The year 2020 was supposed to herald the arrival of self-driving ca rs. Five years earlier, a headline in The
Guardian predicted that “From 2020 you will become a permanent backseat d river” [1]. In 2016 Business
Insider assured us that “10 million self-driving cars will be on the road by 2020 ” [2]. Tesla Motors CEO
Elon Musk promised in 2019 that “A year from now, we’ll have over a millio n cars with full self-driving,
software...everything” [3]. And 2020 was the target announced by s everal automobile companies to bring
self-driving cars to market [4, 5, 6].
Despite attempts to redeﬁne “full self-driving” into existence [7], n one of these predictions has come true. It’s
worth quoting AI expert Drew McDermott on what can happen when over-optimism about AI systems—in
particular, self-driving cars—turns out to be wrong:
Perhaps expectations are too high, and... this will eventually result in disaster. [S]uppose that ﬁve
years from now [funding] collapses miserably as autonomous vehicles fail to roll. Every startup
company fails. And there’s a big backlash so that you can’t get money for anything connected
with AI. Everybody hurriedly changes the names of their research projects to something else.
This condition [is] called the “AI Winter” [8].
What’s most notable is that McDermott’s warning is from 1984, when, like today, the ﬁeld of AI was
awash with conﬁdent optimism about the near future of machine inte lligence. McDermott was writing
about a cyclical pattern in the ﬁeld. New, apparent breakthrough s would lead AI practitioners to predict
rapid progress, successful commercialization, and the near-ter m prospects of “true AI.” Governments and
companies would get caught up in the enthusiasm, and would shower t he ﬁeld with research and development
funding. AI Spring would be in bloom. When progress stalled, the enth usiasm, funding, and jobs would dry
up. AI Winter would arrive. Indeed, about ﬁve years after McDerm ott’s warning, a new AI winter set in.
In this chapter I explore the reasons for the repeating cycle of ov erconﬁdence followed by disappointment
in expectations about AI. I argue that over-optimism among the pu blic, the media, and even experts can
1

--- Page 2 ---
arise from several fallacies in how we talk about AI and in our intuitions about the nature of intelligence.
Understanding these fallacies and their subtle inﬂuences can point t o directions for creating more robust,
trustworthy, and perhaps actually intelligent AI systems.
Springs and Winters
Overconﬁdent predictions about AI are as old as the ﬁeld itself. In 1 958, for example, the New York Times
reported on a demonstration by the US Navy of Frank Rosenblatt’s “perceptron” (a rudimentary precursor
to today’s deep neural networks): “The Navy revealed the embry o of an electronic computer today that it
expects will be able to walk, talk, see, write, reproduce itself, and b e conscious of its existence” [9]. This
optimistic take was quickly followed by similar proclamations from AI pion eers, this time about the promise
of logic-based “symbolic” AI. In 1960 Herbert Simon declared that, “Machines will be capable, within twenty
years, of doing any work that a man can do” [10]. The following year, Claude Shannon echoed this prediction:
“I conﬁdently expect that within a matter of 10 or 15 years, somet hing will emerge from the laboratory which
is not too far from the robot of science ﬁction fame” [11]. And a few y ears later Marvin Minsky forecast that,
“Within a generation...the problems of creating ‘artiﬁcial intelligence’ w ill be substantially solved” [12].
The optimistic AI Spring of the 1960s and early 1970s, reﬂected in th ese predictions, soon gave way to the ﬁrst
AI winter. Minsky and Papert’s 1969 book Perceptrons [13] showed that the kinds of problems solvable by
Rosenblatt’s perceptrons were very limited. In 1973 the Lighthill re port [14] in the UK and the Department
of Defense’s “American Study Group” report in the US, commissione d by their respective governments to
assess prospects for AI in the near future, were both extremely negative about those prospects. This led to
sharp funding decreases and a downturn in enthusiasm for AI in bot h countries.
AI once again experienced an upturn in enthusiasm starting in the ea rly 1980s with several new initiatives:
the rise of “expert systems” in industry [15], Japan’s huge investme nt in its “Fifth Generation” project
[16], which aimed for ambitious AI abilities as the core of a new generatio n of computing systems, the US’s
responding “Strategic Computing Initiative” [17], which provided larg e funding for progress into general AI,
as well as a new set of eﬀorts on neural networks [18, 19], which gen erated new hopes for the ﬁeld.
By the latter part of the 1980s, these optimistic hopes had all been dashed; again, none of these technologies
had achieved the lofty promises that had been made. Expert syste ms, which rely on humans to create rules
that capture expert knowledge of a particular domain, turned out to be brittle—that is, often unable to
generalize or adapt when faced with new situations. The problem was that the human experts writing the
rules actually rely on subconscious knowledge—what we might call “co mmon sense”—that was not part of
the system’s programming. The AI approaches pursued under the Fifth Generation project and Strategic
Computing Initiative ran into similar problems of brittleness and lack of generality. The neural-network
approaches of the 1980s and 1990s likewise worked well on relatively simple examples but lacked the ability
to scale up to complex problems. Indeed, the late 1980’s marked the beginning of a new AI winter, and the
ﬁeld’s reputation suﬀered. When I received my PhD in 1990, I was adv ised not to use the term “artiﬁcial
intelligence” on my job applications.
At the 50th anniversary commemoration of the 1956 Dartmouth Su mmer Workshop that launched the ﬁeld,
AI pioneer John McCarthy, who had originally coined the term “Artiﬁc ial Intelligence,” explained the issue
succinctly: “AI was harder than we thought” [20].
The 1990s and 2000s saw the meteoric rise of machine learning : the development of algorithms that create
predictive models from data. These approaches were typically inspir ed by statistics rather than by neuro-
science or psychology, and were aimed at performing speciﬁc tasks rather than capturing general intelligence.
Machine-learning practitioners were often quick to diﬀerentiate th eir discipline from the then-discredited ﬁeld
of AI.
However, around 2010, deep learning —in which brain-inspired multilayered neural networks are trained fr om
data—emerged from its backwater position and rose to superstar status in machine learning. Deep neural
networks had been around since the 1970s, but only recently, due to huge datasets scraped from the Web,
2

--- Page 3 ---
fast parallel computing chips, and innovations in training methods, c ould these methods scale up to a large
number of previously unsolved AI challenges. Deep neural network s are what power all of the major AI
advances we’ve seen in the past decade, including speech recognitio n, machine translation, chat bots, image
recognition, game playing, and protein folding, among others.
Suddenly the term “AI” started to appear everywhere, and ther e was all at once a new round of optimism
about the prospects of what has been variously called “general,” “t rue,” or “human-level” AI.
In surveys of AI researchers carried out in 2016 and 2018, the me dian prediction of those surveyed gave a
50 percent chance that human-level AI would be created by 2040– 2060, though there was much variance
of opinion, both for sooner and later estimates [21, 22]. Even some o f the most well-known AI experts
and entrepreneurs are in accord. Stuart Russell, co-author of a widely used textbook on AI, predicts that
“superintelligent AI” will “probably happen in the lifetime of my children ” [23] and Sam Altman, CEO
of the AI company OpenAI, predicts that within decades, compute r programs “will do almost everything,
including making new scientiﬁc discoveries that will expand our concep t of ‘everything.’ ” [24] Shane Legg,
co-founder of Google DeepMind, predicted in 2008 that, “Human lev el AI will be passed in the mid-2020s”
[25], and Facebook’s CEO, Mark Zuckerberg, declared in 2015 that “ One of [Facebook’s] goals for the next
ﬁve to 10 years is to basically get better than human level at all of th e primary human senses: vision, hearing,
language, general cognition” [26].
However, in spite of all the optimism, it didn’t take long for cracks to a ppear in deep learning’s fa¸ cade of
intelligence. It turns out that, like all AI systems of the past, deep -learning systems can exhibit brittleness—
unpredictable errors when facing situations that diﬀer from the tr aining data. This is because such systems
are susceptible to shortcut learning [27, 28]: learning statistical associations in the training data that allo w
the machine to produce correct answers but sometimes for the wr ong reasons. In other words, these machines
don’t learn the concepts we are trying to teach them, but rather t hey learn shortcuts to correct answers on
the training set—and such shortcuts will not lead to good generaliza tions. Indeed, deep learning systems
often cannot learn the abstract concepts that would enable them to transfer what they have learned to new
situations or tasks [29]. Moreover, such systems are vulnerable to attack from “adversarial perturbations”
[30]—specially engineered changes to the input that are either imperc eptible or irrelevant to humans, but
that induce the system to make errors.
Despite extensive research on the limitations of deep neural netwo rks, the sources of their brittleness and
vulnerability are still not completely understood. These networks, with their large number of parameters,
are complicated systems whose decision-making mechanisms can be q uite opaque. However, it seems clear
from their non-humanlike errors and vulnerability to adversarial pe rturbations that these systems are not
actually understanding the data they process, at least not in the human sense of “unders tand.” It’s still
a matter of debate in the AI community whether such understandin g can be achieved by adding network
layers and more training data, or whether something more fundame ntal is missing.
At the time of this writing (mid-2021), several new deep-learning ap proaches are once again generating
considerable optimism in the AI community. Some of the hottest new a reas are transformer architectures
using self-supervised (or “predictive”) learning [31], meta-learnin g [32], and deep reinforcement learning [33];
each of these has been cited as progress towards more general, h uman-like AI. While these and other new
innovations have shown preliminary promise, the AI cycle of springs a nd winters is likely to continue. The
ﬁeld continually advances in relatively narrow areas, but the path to ward human-level AI is less clear.
In the next sections I will argue that predictions about the likely time line of human-level AI reﬂect our own
biases and lack of understanding of the nature of intelligence. In pa rticular, I describe four fallacies in our
thinking about AI that seem most central to me. While these fallacies are well-known in the AI community,
many assumptions made by experts still fall victim to these fallacies, and give us a false sense of conﬁdence
about the near-term prospects of “truly” intelligent machines.
3

--- Page 4 ---
Fallacy 1: Narrow intelligence is on a continuum with general intelligence
Advances on a speciﬁc AI task are often described as “a ﬁrst step ” towards more general AI. The chess-
playing computer Deep Blue was “was hailed as the ﬁrst step of an AI r evolution” [34]. IBM described
its Watson system as “a ﬁrst step into cognitive systems, a new era of computing” [35]. OpenAI’s GPT-3
language generator was called a “step toward general intelligence” [36].
Indeed, if people see a machine do something amazing, albeit in a narro w area, they often assume the ﬁeld
is that much further along toward general AI. The philosopher Hub ert Dreyfus (using a term coined by
Yehoshua Bar-Hillel) called this a “ﬁrst-step fallacy.” As Dreyfus cha racterized it, “The ﬁrst-step fallacy is
the claim that, ever since our ﬁrst work on computer intelligence we h ave been inching along a continuum at
the end of which is AI so that any improvement in our programs no mat ter how trivial counts as progress.”
Dreyfus quotes an analogy made by his brother, the engineer Stua rt Dreyfus: “It was like claiming that the
ﬁrst monkey that climbed a tree was making progress towards landin g on the moon” [37].
Like many AI experts before and after him, Dreyfus noted that th e “unexpected obstacle” in the assumed
continuum of AI progress has always been the problem of common sense . I will say more about this barrier
of common sense in the last section.
Fallacy 2: Easy things are easy and hard things are hard
While John McCarthy lamented that “AI was harder than we thought ,” Marvin Minsky explained that this is
because “easy things are hard” [38]. That is, the things that we hum ans do without much thought—looking
out in the world and making sense of what we see, carrying on a conve rsation, walking down a crowded
sidewalk without bumping into anyone—turn out to be the hardest ch allenges for machines. Conversely,
it’s often easier to get machines to do things that are very hard for humans; for example, solving complex
mathematical problems, mastering games like chess and Go, and tra nslating sentences between hundreds
of languages have all turned out to be relatively easier for machines . This is a form of what’s been called
“Moravec’s paradox,” named after roboticist Hans Moravec, who w rote, “It is comparatively easy to make
computers exhibit adult level performance on intelligence tests or p laying checkers, and diﬃcult or impossible
to give them the skills of a one-year-old when it comes to perception a nd mobility” [39].
This fallacy has inﬂuenced thinking about AI since the dawn of the ﬁeld . AI pioneer Herbert Simon pro-
claimed that “Everything of interest in cognition happens above the 100-millisecond level—the time it takes
you to recognize your mother” [40]. Simon is saying that, to underst and cognition, we don’t have to worry
about unconscious perceptual processes. This assumption is reﬂ ected in most of the symbolic AI tradition,
which focuses on the process of reasoning about input that has alr eady been perceived.
In the last decades, symbolic AI approaches have lost favor in the r esearch community, which has largely
been dominated by deep learning, which does address perception. H owever, the assumptions underlying
this fallacy still appear in recent claims about AI. For example, in a 201 6 article, deep-learning pioneer
Andrew Ng was quoted echoing Simon’s assumptions, vastly underes timating the complexity of unconscious
perception and thought: “If a typical person can do a mental tas k with less than one second of thought, we
can probably automate it using AI either now or in the near future” [4 1].
More subtly, researchers at Google DeepMind, in talking about Alpha Go’s triumph, described the game of
Go as one of “the most challenging of domains” [42]. Challenging for who m? For humans, perhaps, but as
psychologist Gary Marcus pointed out, there are domains, including games, that, while easy for humans,
are much more challenging than Go for AI systems. One example is cha rades, which “requires acting skills,
linguistic skills, and theory of mind” [43], abilities that are far beyond an ything AI can accomplish today.
AI is harder than we think, because we are largely unconscious of th e complexity of our own thought
processes. Hans Moravec explains his paradox this way: “Encoded in the large, highly evolved sensory
and motor portions of the human brain is a billion years of experience a bout the nature of the world and
how to survive in it. The deliberate process we call reasoning is, I belie ve, the thinnest veneer of human
4

--- Page 5 ---
thought, eﬀective only because it is supported by this much older an d much more powerful, though usually
unconscious, sensorimotor knowledge. We are all prodigious Olympia ns in perceptual and motor areas, so
good that we make the diﬃcult look easy” [44]. Or more succinctly, Mar vin Minsky notes, “In general, we’re
least aware of what our minds do best” [45].
Fallacy 3: The lure of wishful mnemonics
The term “wishful mnemonic” was coined in a 1976 critique of AI by com puter scientist Drew McDermott:
A major source of simple-mindedness in AI programs is the use of mne monics like “UNDER-
STAND” or “GOAL” to refer to programs and data structures. ...If a researcher...calls the main
loop of his program “UNDERSTAND,” he is (until proven innocent) mer ely begging the ques-
tion. He may mislead a lot of people, most prominently himself. ...What he s hould do instead is
refer to this main loop as “G0034,” and see if he can convince himself or anyone else that G0034
implements some part of understanding. ...Many instructive examples of wishful mnemonics by
AI researchers come to mind once you see the point [46].
Now, many decades later, work on AI is replete with such wishful mne monics—terms associated with human
intelligence that are used to describe the behavior and evaluation of AI programs. Neural networks are
loosely inspired by the brain, but with vast diﬀerences. Machine learning or deep learning methods do not
really resemble learning in humans (or in non-human animals). Indeed, if a machine has learned something
in the human sense of learn, we would expect that it would be able use what it has learned in diﬀeren t
contexts. However, it turns out that this is often not the case. I n machine learning there is an entire subﬁeld
called transfer learning that focuses on the still-open problem of how to enable machines to t ransfer what
they have learned to new situations, an ability that is fundamental t o human learning.
Indeed, the way we talk about machine abilities inﬂuences our concep tions of how general those abilities
really are. Unintentionally providing real-world illustrations of McDerm ott’s warning, one of IBM’s top
executives proclaimed that “Watson can read all of the health-care texts in the world in seconds” [47] and
IBM’s website claims that its Watson program “ understands context and nuance in seven languages” [48].
DeepMind co-founder Demis Hassabis tells us that “AlphaGo’s goal is to beat the best human players not
just mimic them” [49]. And AlphaGo’s lead research David Silver describ ed one of the program’s matches
thus: “We can always ask AlphaGo how well it thinks it’s doing during the game. ...It was only towards the
end of the game that AlphaGo thought it would win ” [50]. (Emphasis is mine in the quotations above.)
One could argue that such anthropomorphic terms are simply short hand: IBM scientists know that Watson
doesn’t read or understand in the way humans do; DeepMind scientis ts know that AlphaGo has no goals or
thoughts in the way humans do, and no human-like conceptions of a “ game” or of “winning.” However, such
shorthand can be misleading to the public trying to understand thes e results (and to the media reporting on
them), and can also unconsciously shape the way even AI experts t hink about their systems and how closely
these systems resemble human intelligence.
McDermott’s “wishful mnemonics” referred to terms we use to des cribe AI programs, but the research
community also uses wishful mnemonics in naming AI evaluation benchm arks after the skills we hope they
test. For example, here are some of the most widely cited current b enchmarks in the subarea of AI called
“natural-language processing” (NLP): the “Stanford Question A nswering Dataset” [51], the “RACE Reading
Comprehension Dataset” [52], and the “General Language Unders tanding Evaluation” [53]. In all of these
benchmarks, the performance of the best machines has already e xceeded that measured for humans (typically
Amazon Mechanical Turk workers). This has led to headlines such as “New AI model exceeds human
performance at question Answering” [54]; “Computers are gettin g better than humans at reading” [55]; and
“Microsoft’s AI model has outperformed humans in natural-langua ge understanding” [56]. Given the names
of these benchmark evaluations, it’s not surprising that people wou ld draw such conclusions. The problem is,
these benchmarks don’t actually measure general abilities for ques tion-answering, reading comprehension, or
natural-language understanding. The benchmarks test only very limited versions of these abilities; moreover,
5

--- Page 6 ---
many of these benchmarks allow machines to learn shortcuts, as I d escribed above—statistical correlations
that machines can exploit to achieve high performance on the test w ithout learning the actual skill being
tested [57, 58]. While machines can outperform humans on these par ticular benchmarks, AI systems are still
far from matching the more general human abilities we associate with the benchmarks’ names.
Fallacy 4: Intelligence is all in the brain
The idea that intelligence is something that can be separated from th e body, whether as a non-physical
substance or as wholly encapsulated in the brain, has a long history in philosophy and cognitive science.
The so-called “information-processing model of mind” arose in psyc hology in the mid-twentieth century.
This model views the mind as a kind of computer, which inputs, stores , processes, and outputs information.
The body does not play much of a role except in the input (perception ) and output (behavior) stages. Under
this view, cognition takes place wholly in the brain, and is, in theory, se parable from the rest of the body.
An extreme corollary of this view is that, in the future, we will be able t o “upload” our brains—and thus
our cognition and consciousness—to computers [59].
The assumption that intelligence can in principle be “disembodied” is implic it in almost all work on AI
throughout its history. One of the most inﬂuential ideas in early AI r esearch was Newell and Simon’s “Phys-
ical Symbol System Hypothesis” (PSSH), which stated: “A physica l symbol system has the necessary and
suﬃcient means for general intelligent action” [60]. The term “physic al symbol system” refers to something
much like a digital computer. The PSSH posits that general intelligenc e can be achieved in digital computers
without incorporating any non-symbolic processes of brain or body . (For an insightful discussion of symbolic
versus subsymbolic processes, see Hofstadter’s “Waking up from the Boolean Dream” [61].)
Newell and Simon’s PSSH was a founding principle of the symbolic approa ch to AI, which dominated the
ﬁeld until the rise of statistical and neurally inspired machine learning in the 1990s and 2000s. However,
these latter non-symbolic approaches also did not view the body as r elevant to intelligence. Instead, neu-
rally inspired approaches from 1980s connectionism to today’s deep neural networks generally assume that
intelligence arises solely from brain structures and dynamics. Today ’s deep neural networks are akin to the
proverbial brain-in-a-vat: passively taking in data from the world a nd outputting instructions for behavior
without actively interacting in the world with any kind of body. Of cour se, robots and autonomous vehicles
are diﬀerent in that they have a physical presence in the world, but to date the kinds of physical interactions
they have, and the feedback to their “intelligence” is quite limited.
The assumption that intelligence is all in the brain has led to speculation that, to achieve human-level
AI, we simply need to scale up machines to match the brain’s “computin g capacity” and then develop the
appropriate “software” for this brain-matching “hardware. For example, one philosopher wrote a report on
the literature that concluded, “I think it more likely than not that 10 15 FLOP/s is enough to perform tasks
as well as the human brain (given the right software, which may be ve ry hard to create)” [62]. No body
needed!
Top AI researchers have echoed the idea that scaling up hardware to match the brain will enable human-
level artiﬁcial intelligence. For example, deep-learning pioneer Geoﬀ rey Hinton predicted, “To understand
[documents] at a human level, we’re probably going to need human-lev el resources and we have trillions of
connections [in our brains]. ...But the biggest networks we have built so far only have billions of connections.
So we’re a few orders of magnitude oﬀ, but I’m sure the hardware pe ople will ﬁx that” [63]. Others have
predicted that the “hardware ﬁx”—the speed and memory capacit y to ﬁnally enable human-level AI—will
come in the form of quantum computers [64].
However, a growing cadre of researchers is questioning the basis o f the “all in the brain” information-
processing model for understanding intelligence and for creating A I. Writing about what he calls “The cul de
sac of the computational metaphor,” computer scientist Rod Broo ks argues, “The reason for why we got stuck
in this cul-de-sac for so long was because Moore’s law just kept feed ing us, and we kept thinking, ‘Oh, we’re
making progress, we’re making progress, we’re making progress.’ B ut maybe we haven’t been” [65]. In fact, a
6

--- Page 7 ---
number of cognitive scientists have argued for decades for the ce ntrality of the body in all cognitive activities.
One prominent proponent of these ideas, the psychologist Mark Jo hnson, writes of a research program on
embodied cognition, gaining steam in the mid-1970s, that “began to provide converging evidence for the
central role of our brains and bodies in everything we experience, t hink, and do” [66]. Psychologist Rebecca
Fincher-Kiefer characterizes the embodied cognition paradigm this way: “Embodied cognition means that
the representation of conceptual knowledge is dependent on the body: it is multimodal..., not amodal,
symbolic, or abstract. This theory suggests that our thoughts a re grounded, or inextricably associated with,
perception, action, and emotion, and that our brain and body work together to have cognition” [67].
The evidence for embodied cognition comes from a diverse set of disc iplines. Research in neuroscience
suggests, for example, that the neural structures controlling c ognition are richly linked to those controlling
sensory and motor systems, and that abstract thinking exploits b ody-based neural “maps” [68]. As neurosci-
entist Don Tucker noted, “There are no brain parts for disembodie d cognition” [69]. Results from cognitive
psychology and linguistics indicate that many, if not all, of our abstra ct concepts are grounded in physical,
body-based internal models [70], revealed in part by the systems of physically based metaphors found in
everyday language [71].
Several other disciplines, such as developmental psychology, add to evidence for embodied cognition. How-
ever, research in AI has mostly ignored these results, though the re is a small group of researchers exploring
these ideas in subareas known as “embodied AI,” “developmental ro botics,” “grounded language understand-
ing,” among others.
Related to the theory of embodied cognition is the idea that the emot ions and the “irrational” biases that
go along with our deeply social lives—typically thought of as separate from intelligence, or as getting in the
way of rationality—are actually key to what makes intelligence possible . AI is often thought of as aiming at
a kind of “pure intelligence,” one that is independent of emotions, irra tionality, and constraints of the body
such as the need to eat and sleep. This assumption of the possibility o f a purely rational intelligence can
lead to lurid predictions about the risks we will face from future “sup erintelligent” machines.
For example, the philosopher Nick Bostrom asserts that a system’s intelligence and its goals are orthogonal;
he argues that “any level of intelligence could be combined with any ﬁn al goal” [72]. As an example,
Bostrom imagines a hypothetical superintelligent AI system whose s ole objective is to produce paperclips;
this imaginary system’s superintelligence enables the invention of inge nious ways to produce paperclips, and
uses up all of the Earth’s resources in doing so.
AI researcher Stuart Russell concurs with Bostrom on the ortho gonality of intelligence and goals. “It is easy
to imagine that a general-purpose intelligent system could be given mo re or less any objective to pursue,
including maximizing the number of paper clips or the number of known d igits of pi” [73]. Russell worries
about the possible outcomes of employing such a superintelligence to solve humanity’s problems: “What
if a superintelligent climate control system, given the job of restor ing carbon dioxide concentrations to
preindustrial levels, believes the solution is to reduce the human pop ulation to zero?...If we insert the wrong
objective into the machine and it is more intelligent than us, we lose” [7 4].
The thought experiments proposed by Bostrom and Russell seem t o assume that an AI system could be
“superintelligent” without any basic humanlike common sense, yet wh ile seamlessly preserving the speed,
precision and programmability of a computer. But these speculation s about superhuman AI are plagued by
ﬂawed intuitions about the nature of intelligence. Nothing in our know ledge of psychology or neuroscience
supports the possibility that “pure rationality” is separable from th e emotions and cultural biases that shape
our cognition and our objectives. Instead, what we’ve learned fro m research in embodied cognition is that
human intelligence seems to be a strongly integrated system with clos ely interconnected attributes, including
emotions, desires, a strong sense of selfhood and autonomy, and a commonsense understanding of the world.
It’s not at all clear that these attributes can be separated.
7

--- Page 8 ---
Conclusions
The four fallacies I have described reveal ﬂaws in our conceptualiza tions of the current state of AI and our
limited intuitions about the nature of intelligence. I have argued that these fallacies are at least in part why
capturing humanlike intelligence in machines always turns out to be har der than we think.
These fallacies raise several questions for AI researchers. How c an we assess actual progress toward “general”
or “human-level” AI? How can we assess the diﬃculty of a particular domain for AI as compared with
humans? How should we describe the actual abilities of AI systems wit hout fooling ourselves and others
with wishful mnemonics? To what extent can the various dimensions o f human cognition (including cognitive
biases, emotions, objectives, and embodiment) be disentangled? H ow can we improve our intuitions about
what intelligence is?
These questions remain open. It’s clear that to make and assess pr ogress in AI more eﬀectively, we will need
to develop a better vocabulary for talking about what machines can do. And more generally, we will need a
better scientiﬁc understanding of intelligence as it manifests in diﬀer ent systems in nature. This will require
AI researchers to engage more deeply with other scientiﬁc discipline s that study intelligence.
The notion of common sense is one aspect of intelligence that has recently been driving collaborat ions between
AI researchers and cognitive scientists from several other discip lines, particularly cognitive development (e.g.,
see [75]). There have been many attempts in the history of AI to give humanlike common sense to machines 1,
ranging from the logic-based approaches of John McCarthy [76] an d Douglas Lenat [77] to today’s deep-
learning-based approaches (e.g., [78]). “Common sense” is what AI r esearcher Oren Etzioni called “the dark
matter of artiﬁcial intelligence,” noting “It’s a little bit ineﬀable, but yo u see its eﬀects on everything” [79].
The term has become a kind of umbrella for what’s missing from today’s state-of-the-art AI systems [80, 81].
While common sense includes the vast amount of knowledge we humans have about the world, it also requires
being able to use that knowledge to recognize and make predictions a bout the situations we encounter, and
to guide our actions in those situations. Giving machines common sens e will require imbuing them with the
very basic “core,” perhaps innate, knowledge that human infants p ossess about space, time, causality, and
the nature of inanimate objects and other living agents [82], the abilit y to abstract from particulars to general
concepts, and to make analogies from prior experience. No one yet knows how to capture such knowledge
or abilities in machines. This is the current frontier of AI research, a nd one encouraging way forward is to
tap into what’s known about the development of these abilities in youn g children. Interestingly, this was
the approach recommended by Alan Turing in his 1950 paper that intr oduced the Turing test. Turing asks,
“Instead of trying to produce a programme to simulate the adult min d, why not rather try to produce one
which simulates the child’s?” [83]
In 1892, the psychologist William James said of psychology at the time, “This is no science; it is only the
hope of a science” [84]. This is a perfect characterization of today ’s AI. Indeed, several researchers have
made analogies between AI and the medieval practice of alchemy. In 1977, AI researcher Terry Winograd
wrote, “In some ways [AI] is akin to medieval alchemy. We are at the s tage of pouring together diﬀerent
combinations of substances and seeing what happens, not yet hav ing developed satisfactory theories...but...it
was the practical experience and curiosity of the alchemists which p rovided the wealth of data from which a
scientiﬁc theory of chemistry could be developed” [85]. Four decad es later, Eric Horvitz, director of Microsoft
Research, concurred: “Right now, what we are doing is not a scienc e but a kind of alchemy” [86]. In order
to understand the nature of true progress in AI, and in particular , why it is harder than we think, we need
to move from alchemy to developing a scientiﬁc understanding of inte lligence.
1Some have questioned why we need machines to havehumanlike cognition, but if we want machines to work with us in our
human world, we will need them to have the same basic knowledge about the world that is the foundation of our own thinking.
8

--- Page 9 ---
Acknowledgments
This material is based upon work supported by the National Science Foundation under Grant No. 2020103.
Any opinions, ﬁndings, and conclusions or recommendations expres sed in this material are those of the author
and do not necessarily reﬂect the views of the National Science Fou ndation. This work was also supported
by the Santa Fe Institute. I am grateful to Philip Ball, Rodney Brook s, Daniel Dennett, Stephanie Forrest,
Douglas Hofstadter, Tyler Millhouse, and Jacob Springer for comme nts on an earlier draft of this manuscript.
References
[1] T. Adams. Self-driving cars: From 2020 you will become a permane nt backseat driver. The Guardian ,
2015. URL https://tinyurl.com/zepc5spz.
[2] 10 million self-driving cars will be on the road by 2020. Business Insider Intelligence , 2020. URL
https://tinyurl.com/9mr6x8zk.
[3] A. J. Hawkins. Here are Elon Musk’s wildest predictions about Tesla ’s self-driving cars. The Verge ,
2019. URL https://tinyurl.com/4ap2rm2n.
[4] R. McCormick. NVIDIA is working with Audi to get you a self-driving car by 2020. The Verge , 2017.
URL https://tinyurl.com/3epbpaz3.
[5] Y. Kageyama. CEO: Nissan will be ready with autonomous driving by 2020. Phys.Org, 2015. URL
https://phys.org/news/2015-05-ceo-nissan-ready-auto nomous.html.
[6] S. Eagell. https://tinyurl.com/psxwhhnb, 2020.
[7] R. Baldwin. Tesla tells California DMV that FSD is not capable of auton omous driving. Car and
Driver, 2021. URL https://tinyurl.com/p8aw9jke.
[8] McDermott D., M. M. Waldrop, B. Chandrasekaran, J. McDermot t, and R. Schank. The dark ages of
AI: A panel discussion at AAAI-84. AI Magazine , 6(3):122–134, 1985.
[9] New Navy Device Learns by Doing. New York Times , 1958. URL https://tinyurl.com/yjh3eae8.
[10] H. A. Simon. The Ford Distinguished Lectures, Volume 3: The New Science o f Management Decision .
Harper and Brothers, p. 38, 1960.
[11] The Shannon Centennial: 1100100 years of bits. https://www.youtube.com/watch?v=pHSRHi17RKM,
1961.
[12] M. L. Minsky. Computation: Finite and Inﬁnite Machines . Prentice-Hall, p. 2, 1967.
[13] M. L. Minsky and S. A Papert. Perceptrons: An Introduction to Computational Geometry . MIT press,
1969.
[14] J. Lighthill. Artiﬁcial intelligence: A general survey. In Artiﬁcial Intelligence: A Paper Symposium .
Science Research Council, 1973.
[15] J. Durkin. Expert systems: A view of the ﬁeld. IEEE Annals of the History of Computing , 11(02):
56–63, 1996.
[16] B. R. Gaines. Perspectives on Fifth Generation computing. Oxford Surveys in Information Technology ,
1:1–53, 1984.
[17] M. Steﬁk. Strategic computing at DARPA: Overview and assess ment. Communications of the ACM ,
28(7):690–704, 1985.
9

--- Page 10 ---
[18] J. L. McClelland, D. E. Rumelhart, and the PDP Research Group. Parallel Distributed Processing,
Vol.1: Foundations . MIT press Cambridge, MA, 1986.
[19] J. L. McClelland, D. E. Rumelhart, and the PDP Research Group. Parallel Distributed Processing,
Vol.2: Psychological and Biological Models . MIT press Cambridge, MA, 1986.
[20] C. Moewes and A. N¨ urnberger. Computational Intelligence in Intelligent Data Analysis . Springer, p.
135, 2013.
[21] V. C. M¨ uller and N. Bostrom. Future progress in artiﬁcial intellig ence: A survey of expert opinion. In
V. C. M¨ uller, editor, Fundamental Issues of Artiﬁcial Intelligence , pages 555–572. Springer, 2016.
[22] K. Grace, J. Salvatier, A. Dafoe, B. Zhang, and O. Evans. Whe n will AI exceed human performance?
Evidence from AI experts. Journal of Artiﬁcial Intelligence Research , 62:729–754, 2018.
[23] S. Russell. Human Compatible: Artiﬁcial Intelligence and the Problem o f Control . Penguin, p. 77, 2019.
[24] https://moores.samaltman.com, 2021.
[25] J. Despres. Scenario: Shane Legg. Future, 2008. URL https://tinyurl.com/hwzna364.
[26] H. McCracken. Inside Mark Zuckerberg’s bold plan for the futu re of Facebook. Fast Company , 2015.
URL www.fastcompany.com/3052885/mark-zuckerberg-faceboo k.
[27] R. Geirhos, J.-H. Jacobsen, C. Michaelis, R. Zemel, W. Brendel, M . Bethge, and F. A. Wichmann.
Shortcut learning in deep neural networks. Nature Machine Intelligence , 2(11):665–673, 2020.
[28] S. Lapuschkin, S. W¨ aldchen, A. Binder, G. Montavon, W. Same k, and K.-R. M¨ uller. Unmasking Clever
Hans predictors and assessing what machines really learn. Nature Communications, 10(1):1–8, 2019.
[29] M. Mitchell. Abstraction and analogy-making in artiﬁcial intelligenc e. arXiv:2102.10717, 2021.
[30] S. M. Moosavi-Dezfooli, A. Fawzi, O. Fawzi, and P. Frossard. Un iversal adversarial perturbations.
In Proceedings of the IEEE Conference on Computer Vision and Pa ttern Recognition (CVPR) , pages
1765–1773, 2017.
[31] J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova. BERT: Pre-t raining of deep bidirectional trans-
formers for language understanding. arXiv:1810.04805, 2018.
[32] C. Finn, P. Abbeel, and S. Levine. Model-agnostic meta-learning for fast adaptation of deep networks.
In Proceedings of the International Conference on Machine Lea rning (ICML) , pages 1126–1135, 2017.
[33] K. Arulkumaran, M. P. Deisenroth, M. Brundage, and A. A. Bha rath. A brief survey of deep reinforce-
ment learning. IEEE Signal Processing Magazine , 34, 2017.
[34] J. Aron. AI landmark as Googlebot beats top human at ancient g ame of Go. New Scientist , 2016. URL
https://tinyurl.com/2ztrk6hv.
[35] https://tinyurl.com/45fs8a7e, 2013.
[36] https://tinyurl.com/36rkhzrz, 2019.
[37] Hubert L Dreyfus. A history of ﬁrst step fallacies. Minds and Machines , 22(2):87–99, 2012.
[38] M. Minsky. The Society of Mind . Simon and Schuster, p. 29, 1987.
[39] H. Moravec. Mind Children: The Future of Robot and Human Intelligence . Harvard University Press,
p. 15, 1988.
[40] D. R. Hofstadter. Metamagical Themas: Questing for the Essence of Mind and Pat tern. Basic Books,
p. 632, 1985.
10

--- Page 11 ---
[41] A. Ng. What artiﬁcial intelligence can and can’t do right now. Harvard Business Review , 2016. URL
https://tinyurl.com/udnzhuk.
[42] D. Silver et al. Mastering the game of Go without human knowledge . Nature, 550(7676):354–359, 2017.
[43] G. Marcus. Innateness, Alphazero, and artiﬁcial intelligence. arXiv:1801.05667, 2018.
[44] H. Moravec. Mind Children: The Future of Robot and Human Intelligence . Harvard University Press,
pp. 15–16, 1988.
[45] Minsky, M. Decentralized minds. Behavioral and Brain Sciences , 3(3):439–440, 1980.
[46] D. McDermott. Artiﬁcial intelligence meets natural stupidity. ACM SIGART Bulletin , (57):4–9, 1976.
[47] S. Gustin. IBM’s Watson supercomputer wins practice Jeopard y round. Wired, 2011.
[48] https://www.ibm.com/cognitive/stories/bots/stories/sciencefact/.
[49] Mixed outlook for human-versus-AI match. Korea Herald, 2016. URL https://tinyurl.com/zb3ywabe.
[50] S. Shead. Google DeepMind is edging towards a 3-0 victory agains t world Go champion Ke Jie. Business
Insider, 2017. URL https://tinyurl.com/svb7x7e6.
[51] https://rajpurkar.github.io/SQuAD-explorer/.
[52] https://www.cs.cmu.edu/~glai1/data/race/.
[53] https://gluebenchmark.com/.
[54] D. Costenaro. New AI model exceeds human performance at q uestion answering. BecomingHuman.ai,
2018. URL https://tinyurl.com/ujwp6s95.
[55] S. Pham. Computers are getting better than humans at readin g. CNN Business , 2018. URL
https://tinyurl.com/k48xa8nj.
[56] U. Jawad. Microsoft’s AI model has outperformed humans in na tural language understanding. Neowin,
2021. URL https://tinyurl.com/2x4r54ad.
[57] T. McCoy, E. Pavlick, and T. Linzen. Right for the wrong reason s: Diagnosing syntactic heuristics in
natural language inference. In Proceedings of the 57th Annual Meeting of the Association fo r Computa-
tional Linguistics (ACL) , pages 3428–3448, 2019.
[58] T. Linzen. How can we accelerate progress towards human-like linguistic generalization? In Proceedings
of the 58th Annual Meeting of the Association for Computatio nal Linguistics (ACL) , pages 5210–5217,
2020.
[59] V. Woollaston. We’ll be uploading our entire minds to computers by 2045 and our bodies
will be replaced by machines within 90 years, Google expert claims. Daily Mail , 2013. URL
https://tinyurl.com/ht44uxzv.
[60] A. Newell and H. A. Simon. Computer science as empirical inquiry: Symbols and search. Communica-
tions of the ACM , 19:113–126, 1976.
[61] D. R. Hofstadter. Waking up from the Boolean dream, or, subc ognition as computation, 1985. Chapter
26 of Metamagical Themas , Basic Books.
[62] J. Carlsmith. New report on how much computational power it ta kes to match the human brain.
https://www.openphilanthropy.org/blog/new-report-br ain-computation, 2020.
[63] J. Patterson and A. Gibson. Deep Learning: A Practitioner’s Approach . O’Reilly Media, p. 231, 2017.
11

--- Page 12 ---
[64] G. Musser. Job one for quantum computers: Boost artiﬁcial in telligence. Quanta Magazine , 2018. URL
https://tinyurl.com/2k8fw628.
[65] The cul-de-sac of the computational metaphor. https://tinyurl.com/rjtumkca, 2019.
[66] Mark Johnson. Embodied Mind, Meaning, and Reason: How Our Bodies Give Rise to Understanding .
University of Chicago Press, 2017.
[67] Rebecca Fincher-Kiefer. How the Body Shapes Knowledge: Empirical Support for Embodi ed Cognition .
American Psychological Association, 2019.
[68] R. A. Epstein, E. Z. Patai, J. B. Julian, and H. J. Spiers. The cog nitive map in humans: spatial
navigation and beyond. Nature Neuroscience, 20(11):1504, 2017.
[69] D. M. Tucker. Mind from Body: Experience from Neural Structure . Oxford University Press, 2007.
[70] L. W. Barsalou and K. Wiemer-Hastings. Situating abstract con cepts. In Grounding Cognition: The Role
of Perception and Action in Memory, Language, and Thought , pages 129–163. Cambridge University
Press, 2005.
[71] G. Lakoﬀ and M. Johnson. Metaphors We Live By . University of Chicago Press, 2008.
[72] N. Bostrom. Superintelligence: Paths, Dangers, Strategies . Oxford University Press, p. 105, 2014.
[73] S. Russell. Human Compatible: Artiﬁcial Intelligence and the Problem o f Control . Penguin, p. 167,
2019.
[74] S. Russell. How to stop superhuman A.I. before it stops us. New York Times , 2019. URL
https://www.nytimes.com/2019/10/08/opinion/artificial-intelligence.html.
[75] M. Turek. Machine common sense. https://www.darpa.mil/program/machine-common-sense.
[76] J. McCarthy. Programs with common sense. In Readings In Knowledge Representation . Morgan Kauf-
mann, 1986.
[77] D. B. Lenat, R. V. Guha, K. Pittman, D. Pratt, and M. Shepher d. CYC: Toward programs with
common sense. Communications of the ACM , 33(8):30–49, 1990.
[78] R. Zellers, Y. Bisk, A. Farhadi, and Y. Choi. From recognition to c ognition: Visual commonsense rea-
soning. In Proceedings of the IEEE Conference on Computer Vision and Pa ttern Recognition (CVPR) ,
pages 6720–6731, 2019.
[79] W. Knight. The US military wants to teach AI some basic common se nse. Technology Review, 2018.
URL https://tinyurl.com/2xuvxefe.
[80] E. Davis and G. Marcus. Commonsense reasoning and commonse nse knowledge in artiﬁcial intelligence.
Communications of the ACM , 58(9):92–103, 2015.
[81] H. J. Levesque. Common Sense, the Turing Test, and the Quest for Real AI . MIT Press, 2017.
[82] E. S. Spelke and K. D. Kinzler. Core knowledge. Developmental Science , 10(1):89–96, 2007.
[83] A. M. Turing. Computing machinery and intelligence. Mind, 59(236):433–460, 1950.
[84] W. James. Psychology: The Briefer Course . Henry Holt, p. 335, 1892.
[85] T. Winograd. On some contested suppositions of generative ling uistics about the scientiﬁc study of
language. Cognition, 5(2):151–79, 1977.
[86] C. Metz. A new way for machines to see, taking shape in Toronto . New York Times , 2017. URL
https://tinyurl.com/5bwd3u9n.
12